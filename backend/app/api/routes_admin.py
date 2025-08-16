"""\
app/api/routes_admin.py — Admin-Endpunkte

Funktionen:
- GET  /admin/status    → Modell-/Index-/Zähl- und Konfigstatus
- POST /admin/config    → Laufzeit-Konfiguration (Device wechseln, Score-Flags)
- POST /admin/reindex   → Indizes (Abstracts/Authors) aus DB neu aufbauen
- POST /admin/reset     → Datenbank leeren & leere Indizes initialisieren
- POST /admin/loglevel  → Globales Logging-Level zur Laufzeit ändern
"""
from __future__ import annotations

# ── Standardbibliothek
import logging
import os
from typing import Any, Dict

# ── Drittanbieter
import torch
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy import func, text
from sqlmodel import SQLModel, Session

# ── Lokale Module
from app.config import settings
from app.db.base import engine, get_session
from app.embeddings.encoder import load_model
from app.index.service import IndexService, MultiIndex
from app.models.domain import Abstract, Author


# ----------------------------------------------------------------------------
# Logger
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/admin", tags=["admin"])


# ────────────────────────────────────────────────────────────────────────────────
# Status
# ────────────────────────────────────────────────────────────────────────────────
@router.get("/status")
async def admin_status(
    request: Request, session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Aggregierter Admin-Status zu Modell, DB-Zählern, Indizes & Config."""
    logger.info("GET /admin/status")

    try:
        abstract_count = session.query(func.count(Abstract.id)).scalar() or 0
        author_count = session.query(func.count(Author.id)).scalar() or 0
    except Exception:
        logger.exception("/admin/status: DB-Count fehlgeschlagen")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="count_failed")

    aidx = getattr(request.app.state, "abstract_index", None)
    auidx = getattr(request.app.state, "author_index", None)

    logger_level = logging.getLogger().getEffectiveLevel()
    level_name = logging.getLevelName(logger_level)

    result = {
        "model": {
            "name": getattr(request.app.state, "model_name", "unknown"),
            "device": getattr(request.app.state, "model_device", "cpu"),
            "available": {
                "cpu": True,
                "cuda": torch.cuda.is_available(),
                "mps": torch.backends.mps.is_available(),
            },
        },
        "counts": {"abstracts": int(abstract_count), "authors": int(author_count)},
        "indices": {
            "abstracts": int(getattr(aidx, "ntotal", 0) or 0),
            "authors": int(getattr(auidx, "ntotal", 0) or 0),
        },
        "config": {
            "show_scores": bool(getattr(request.app.state, "show_scores", False)),
            "score_mode": getattr(request.app.state, "score_mode", "cosine"),
        },
        "logger": {"level": level_name},
    }

    logger.debug("/admin/status: counts=%s indices=%s", result["counts"], result["indices"])
    return result


# ────────────────────────────────────────────────────────────────────────────────
# Laufzeit-Konfiguration
# ────────────────────────────────────────────────────────────────────────────────
@router.post("/config")
async def admin_config(request: Request, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Konfiguriert Modell-Device und UI-Flags zur Laufzeit."""
    logger.info("POST /admin/config: keys=%s", list(payload.keys()))

    device = payload.get("device")
    if device is not None:
        device = str(device)
        if device not in {"cpu", "cuda", "mps"}:
            logger.warning("/admin/config: invalid_device=%s", device)
            raise HTTPException(status_code=400, detail="invalid_device")
        if device == "cuda" and not torch.cuda.is_available():
            logger.warning("/admin/config: cuda_unavailable")
            raise HTTPException(status_code=400, detail="cuda_unavailable")
        if device == "mps" and not torch.backends.mps.is_available():
            logger.warning("/admin/config: mps_unavailable")
            raise HTTPException(status_code=400, detail="mps_unavailable")

        model_name = getattr(request.app.state, "model_name", settings.EMBED_MODEL)
        try:
            logger.info("/admin/config: Lade Modell '%s' auf '%s'", model_name, device)
            model, actual = load_model(model_name=model_name, device=device)
            request.app.state.model = model
            request.app.state.model_device = actual
            request.app.state.model_name = model_name
            logger.debug("/admin/config: Modell geladen, actual_device=%s", actual)
        except Exception:
            logger.exception("/admin/config: Modell-Ladevorgang fehlgeschlagen")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="model_load_failed")

    if "show_scores" in payload:
        request.app.state.show_scores = bool(payload["show_scores"])
        logger.debug("/admin/config: show_scores=%s", request.app.state.show_scores)

    if payload.get("score_mode") in ("cosine", "faiss"):
        request.app.state.score_mode = payload["score_mode"]
        logger.debug("/admin/config: score_mode=%s", request.app.state.score_mode)

    result = {
        "status": "ok",
        "model": {
            "name": getattr(request.app.state, "model_name", ""),
            "device": getattr(request.app.state, "model_device", ""),
        },
        "config": {
            "show_scores": bool(getattr(request.app.state, "show_scores", False)),
            "score_mode": getattr(request.app.state, "score_mode", "cosine"),
        },
    }
    return result


# ────────────────────────────────────────────────────────────────────────────────
# Reindex
# ────────────────────────────────────────────────────────────────────────────────
@router.post("/reindex")
async def reindex(request: Request) -> Dict[str, Any]:
    """Rebuild der FAISS-Indizes (Abstracts + Autor:innen) aus der aktuellen DB."""
    dim = settings.VECTOR_DIM
    metric = "l2"  # konsistent mit dem faiss_score_from_l2-Pfad

    abs_path = os.path.join(settings.INDEX_DIR, "abstracts.index")
    auth_path = os.path.join(settings.INDEX_DIR, "authors.index")
    os.makedirs(settings.INDEX_DIR, exist_ok=True)

    logger.info("POST /admin/reindex: dim=%s metric=%s dir=%s", dim, metric, settings.INDEX_DIR)

    # Vorhandene Index-Dateien löschen, um einen echten Neuaufbau zu erzwingen
    for p in (abs_path, auth_path):
        try:
            if os.path.exists(p):
                os.remove(p)
                logger.debug("/admin/reindex: removed %s", p)
        except Exception:
            # tolerant – bei fehlenden Rechten/Locks nicht hart abbrechen, aber loggen
            logger.exception("/admin/reindex: remove failed for %s", p)

    try:
        # Neue Services mit Zielpfaden
        abs_service = IndexService(dim=dim, metric=metric, index_path=abs_path)
        auth_service = IndexService(dim=dim, metric=metric, index_path=auth_path)
        request.app.state.indices = MultiIndex(abs_service, auth_service)

        # Aus DB aufbauen
        with Session(engine) as s:
            request.app.state.indices.load_or_build(s)

        # Backwards-Compat: alte Aliasse aktualisieren
        request.app.state.abstract_index = request.app.state.indices.abs.index
        request.app.state.author_index = request.app.state.indices.auth.index

        # Persistieren
        request.app.state.indices.save()

        abs_n = getattr(request.app.state.abstract_index, "ntotal", 0)
        auth_n = getattr(request.app.state.author_index, "ntotal", 0)
        logger.info("/admin/reindex: fertig — abstracts=%s authors=%s", abs_n, auth_n)

        return {"status": "ok", "indices": {"abstracts": abs_n, "authors": auth_n}}
    except HTTPException:
        raise
    except Exception:
        logger.exception("/admin/reindex: Fehler beim Neuaufbau der Indizes")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="reindex_failed")


# ────────────────────────────────────────────────────────────────────────────────
# Reset
# ────────────────────────────────────────────────────────────────────────────────
@router.post("/reset")
async def admin_reset(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Leert die Datenbank und initialisiert leere Indizes.

    Sicherheitsmechanismus: `{"confirm": "RESET"}` erforderlich.
    """
    logger.warning("POST /admin/reset aufgerufen")

    if payload.get("confirm") != "RESET":
        logger.warning("/admin/reset: confirmation_required")
        raise HTTPException(status_code=400, detail="confirmation_required")

    # Alle Tabellen löschen & IDs zurücksetzen
    table_names = [t.name for t in SQLModel.metadata.sorted_tables]
    if not table_names:
        logger.error("/admin/reset: no_tables_found")
        raise HTTPException(status_code=500, detail="no_tables_found")

    stmt = "TRUNCATE TABLE " + ", ".join(table_names) + " RESTART IDENTITY CASCADE;"
    try:
        session.exec(text(stmt))
        session.commit()
        logger.info("/admin/reset: DB geleert (%s Tabellen)", len(table_names))
    except Exception:
        session.rollback()
        logger.exception("/admin/reset: Fehler beim TRUNCATE")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="truncate_failed")

    # Neue, leere Index-Services
    try:
        abs_service = IndexService(
            dim=settings.VECTOR_DIM,
            metric="l2",
            index_path=os.path.join(settings.INDEX_DIR, "abstracts.index"),
        )
        auth_service = IndexService(
            dim=settings.VECTOR_DIM,
            metric="l2",
            index_path=os.path.join(settings.INDEX_DIR, "authors.index"),
        )
        request.app.state.indices = MultiIndex(abs_service, auth_service)

        # Kompatibilitäts-Aliasse zurücksetzen
        request.app.state.abstract_index = request.app.state.indices.abs.index
        request.app.state.author_index = request.app.state.indices.auth.index
        logger.debug("/admin/reset: leere Indizes initialisiert")
    except Exception:
        logger.exception("/admin/reset: Fehler bei Index-Initialisierung")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="index_init_failed")

    return {
        "status": "ok",
        "message": "database_cleared",
        "counts": {"abstracts": 0, "authors": 0},
        "indices": {"abstracts": 0, "authors": 0},
    }


# ────────────────────────────────────────────────────────────────────────────────
# Log-Level zur Laufzeit setzen
# ────────────────────────────────────────────────────────────────────────────────
@router.post("/loglevel")
async def set_loglevel(payload: Dict[str, Any] = Body(...)) -> Dict[str, str]:
    """Ändert das globale Logging-Level zur Laufzeit.

    Payload: {"level": "DEBUG"}  # oder INFO, WARNING, ERROR, CRITICAL
    """
    level_name = str(payload.get("level", "INFO")).upper()
    logger.info("POST /admin/loglevel: level=%s", level_name)

    if not hasattr(logging, level_name):
        logger.warning("/admin/loglevel: invalid_level=%s", level_name)
        raise HTTPException(status_code=400, detail="invalid_level")

    logging.getLogger().setLevel(getattr(logging, level_name))
    logger.debug("/admin/loglevel: global level gesetzt")
    return {"status": "ok", "new_level": level_name}
