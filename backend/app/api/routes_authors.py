"""\
app/api/routes_authors.py — Routen für Autoren-Suche, Detail, Ähnlichkeit & Mutation

Ziele:
- /authors/search: Paginierte Volltext-/Vektor-Suche nach Autoren
- /authors/{id}: Detailansicht inkl. Abstracts & Topics
- /authors/{id}/similar: ähnliche Autor:innen (Vektorraum)
- /authors/{id} [PATCH]: Name ändern, optional Embedding neu berechnen & indexieren
- /authors/{id} [DELETE]: Autor:in + Links löschen und aus Index entfernen
"""

from __future__ import annotations

# ── Standardbibliothek
import logging
from typing import Any, Dict, List

# ── Drittanbieter
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

# ── Lokale Module
from app.db.base import get_session
from app.models.domain import Abstract, AbstractAuthorLink, Author
from app.services.search_service import search_authors_service, similar_authors_service


# ----------------------------------------------------------------------------
# Logger
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------------
router = APIRouter(tags=["authors"])  # Gruppiert die Routen im OpenAPI-UI


# ────────────────────────────────────────────────────────────────────────────────
# Suche
# ────────────────────────────────────────────────────────────────────────────────
@router.get("/search")
async def search_authors(
    request: Request,
    keyword: str = Query(..., description="Suchbegriff"),
    page: int = Query(1, ge=1, description="1-basierter Seitenindex"),
    page_size: int = Query(10, ge=1, le=100, description="Ergebnisse pro Seite"),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Sucht Autor:innen nach `keyword` mit Pagination.

    Delegiert an `search_authors_service` (enthält i. d. R. Volltext- und/oder
    Vektor-Suche). Bewahrt hier die Endpoint-Deklaration schlank.
    """
    client_ip = getattr(request.client, "host", "-")
    logger.info("/authors/search: keyword='%s' page=%s size=%s ip=%s", keyword, page, page_size, client_ip)

    try:
        result = await search_authors_service(request, session, keyword, page, page_size)
        logger.debug("/authors/search: result_keys=%s", list(result.keys()))
        return result
    except Exception:
        logger.exception("/authors/search: unerwarteter Fehler bei der Suche")
        # Generische Fehlermeldung ohne interne Details
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="search_failed")


# ────────────────────────────────────────────────────────────────────────────────
# Detailansicht
# ────────────────────────────────────────────────────────────────────────────────
@router.get("/{author_id}")
async def get_author_detail(
    author_id: int, session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Detail zu einer/m Autor:in inkl. Abstract-Liste mit Topics.

    Lädt die Author-Entität sowie die zugehörigen Abstracts (inkl. Topics) in
    sinnvoller Reihenfolge (neuere/IDs zuerst).
    """
    logger.info("GET /authors/%s", author_id)

    author = session.get(Author, author_id)
    if not author:
        logger.warning("GET /authors/%s: author_not_found", author_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="author_not_found")

    # Lade Abstracts mit Topics in einem Roundtrip (selectinload ist effizient
    # für 1-N Relationen, reduziert N+1-Queries)
    abs_rows: List[Abstract] = (
        session.query(Abstract)
        .options(selectinload(Abstract.topics))
        .join(AbstractAuthorLink, AbstractAuthorLink.abstract_id == Abstract.id)
        .filter(AbstractAuthorLink.author_id == author_id)
        .order_by(
            Abstract.publication_date.desc().nullslast(),
            Abstract.id.desc(),
        )
        .all()
    )

    response: Dict[str, Any] = {
        "id": author.id,
        "name": author.name,
        "abstract_count": len(abs_rows),
        "abstracts": [
            {
                "id": a.id,
                "title": a.title,
                "session_title": a.session_title,
                "publication_date": a.publication_date.isoformat() if a.publication_date else None,
                "topics": [{"id": t.id, "title": t.title} for t in a.topics],
            }
            for a in abs_rows
        ],
    }

    logger.debug("GET /authors/%s: %s abstracts geliefert", author_id, len(abs_rows))
    return response


# ────────────────────────────────────────────────────────────────────────────────
# Ähnliche Autor:innen
# ────────────────────────────────────────────────────────────────────────────────
@router.get("/{author_id}/similar")
async def get_similar_authors(
    request: Request,
    author_id: int,
    top_k: int = Query(5, ge=1, le=50, description="Max. Anzahl ähnlicher Autor:innen"),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Gibt bis zu `top_k` ähnliche Autor:innen zurück (Vektorraum)."""
    client_ip = getattr(request.client, "host", "-")
    logger.info("GET /authors/%s/similar: top_k=%s ip=%s", author_id, top_k, client_ip)

    try:
        result = await similar_authors_service(request, session, author_id, top_k)
        logger.debug("GET /authors/%s/similar: result_keys=%s", author_id, list(result.keys()))
        return result
    except HTTPException:
        # bereits korrekt gethrowt (z. B. bei unbekanntem Autor)
        raise
    except Exception:
        logger.exception("GET /authors/%s/similar: unerwarteter Fehler", author_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="similar_failed")


# ────────────────────────────────────────────────────────────────────────────────
# Patch
# ────────────────────────────────────────────────────────────────────────────────
@router.patch("/{author_id}")
async def patch_author(
    author_id: int,
    request: Request,
    payload: Dict[str, Any] = Body(..., description="Felder: name (str), recompute (bool)"),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Aktualisiert Author-Attribute (derzeit: `name`).

    Optional: Embeddings/Index neu aufbauen, wenn `recompute: true` gesetzt ist.
    """
    logger.info("PATCH /authors/%s: payload_keys=%s", author_id, list(payload.keys()))

    a = session.get(Author, author_id)
    if not a:
        logger.warning("PATCH /authors/%s: author_not_found", author_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="author_not_found")

    # Name aktualisieren (bewusst einfache Normalisierung)
    if "name" in payload:
        a.name = str(payload["name"]).strip()

    try:
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("PATCH /authors/%s: commit für Name fehlgeschlagen", author_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="update_failed")

    # Optional: Embedding als Mean über Author-Abstract-Embeddings neu berechnen
    recompute = bool(payload.get("recompute", False))
    if recompute:
        logger.info("PATCH /authors/%s: recompute Embedding angefordert", author_id)

        abs_rows: List[Abstract] = session.exec(
            select(Abstract)
            .join(AbstractAuthorLink, AbstractAuthorLink.abstract_id == Abstract.id)
            .where(
                AbstractAuthorLink.author_id == author_id,
                Abstract.embedding != None,  # noqa: E711 — SQLAlchemy-ISNULL Semantik
            )
        ).all()

        if abs_rows:
            import numpy as np  # Import lokal halten, um Importkosten nur bei Bedarf zu zahlen

            vecs = np.asarray([r.embedding for r in abs_rows], dtype=np.float32)
            mean_vec = vecs.mean(axis=0)
            a.embedding = mean_vec.tolist()
            try:
                session.commit()
                logger.debug("PATCH /authors/%s: %s Abstract-Embeddings gemittelt", author_id, len(abs_rows))
            except Exception:
                session.rollback()
                logger.exception("PATCH /authors/%s: commit für Embedding fehlgeschlagen", author_id)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="embedding_update_failed")

            # Index upsert (synchron). Defensive: Index-Komponente könnte fehlen.
            try:
                index = getattr(getattr(request.app.state, "indices", None), "auth", None)
                if index is None:
                    logger.warning("PATCH /authors/%s: Index-Komponente fehlt, skip add_or_update", author_id)
                else:
                    index.add_or_update([a.id], [mean_vec])
                    logger.debug("PATCH /authors/%s: Index add_or_update OK", author_id)
            except Exception:
                # Fehler beim Upsert nicht fatal fürs API-Ergebnis; wird geloggt
                logger.exception("PATCH /authors/%s: Index add_or_update fehlgeschlagen", author_id)
        else:
            logger.info("PATCH /authors/%s: keine Abstract-Embeddings vorhanden — recompute übersprungen", author_id)

    return {"status": "ok", "id": a.id, "recomputed": recompute}


# ────────────────────────────────────────────────────────────────────────────────
# Delete
# ────────────────────────────────────────────────────────────────────────────────
@router.delete("/{author_id}")
async def delete_author(
    author_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Löscht Autor:in und Linkeinträge; bereinigt den Author-Index.

    Abstracts bleiben unverändert erhalten.
    """
    logger.info("DELETE /authors/%s", author_id)

    a = session.get(Author, author_id)
    if not a:
        logger.warning("DELETE /authors/%s: author_not_found", author_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="author_not_found")

    # Links löschen (bulk)
    try:
        (
            session.query(AbstractAuthorLink)
            .where(AbstractAuthorLink.author_id == author_id)
            .delete(synchronize_session=False)
        )
        # Author löschen
        session.delete(a)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("DELETE /authors/%s: DB-Operation fehlgeschlagen", author_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="delete_failed")

    # Index bereinigen (defensiv)
    try:
        index = getattr(getattr(request.app.state, "indices", None), "auth", None)
        if index is None:
            logger.warning("DELETE /authors/%s: Index-Komponente fehlt, skip remove", author_id)
        else:
            index.remove([author_id])
            logger.debug("DELETE /authors/%s: Index remove OK", author_id)
    except Exception:
        # Loggen, aber Response bleibt 200 — Daten sind in der DB weg
        logger.exception("DELETE /authors/%s: Index remove fehlgeschlagen", author_id)

    return {"status": "ok", "deleted": author_id}
