"""\
app/index/index_hooks.py — Inkrementelle Index-Aktualisierung nach Datenänderungen

Aufgaben dieses Moduls:
- Ableiten/Aktualisieren von Autoren-Embeddings als Mean über deren Abstract-Embeddings
- Upserts in die FAISS-Indizes für Abstracts und Autoren (IDMap2, Flat-Backends)
- Deduplizierung innerhalb eines Batches (FAISS verlangt eindeutige IDs)
"""

from __future__ import annotations

# ── Standardbibliothek
import logging
from typing import Iterable, List, Tuple

# ── Drittanbieter
import numpy as np
from fastapi import FastAPI
from sqlmodel import Session, select

# ── Lokale Module
from app.models.domain import Abstract, AbstractAuthorLink, Author


# ────────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ────────────────────────────────────────────────────────────────────────────────

def _mean_author_embedding(session: Session, author_id: int) -> np.ndarray | None:
    """Mittelwert der Embeddings aller Abstracts einer/s Autor:in.

    Gibt ``None`` zurück, wenn kein Abstract ein Embedding hat.
    """
    rows = (
        session.query(Abstract.embedding)
        .join(AbstractAuthorLink, AbstractAuthorLink.abstract_id == Abstract.id)
        .filter(
            AbstractAuthorLink.author_id == author_id,
            Abstract.embedding != None,  # noqa: E711 — SQLAlchemy IS NOT NULL
        )
        .all()
    )
    if not rows:
        return None
    vecs = np.asarray([np.asarray(r[0], dtype=np.float32) for r in rows], dtype=np.float32)
    return vecs.mean(axis=0)


def _ensure_2d_contiguous(vecs: np.ndarray) -> np.ndarray:
    """Sorgt dafür, dass Vektoren 2D (N, D) und C-contiguous (float32) sind."""
    arr = np.asarray(vecs, dtype=np.float32)
    arr = np.atleast_2d(arr)
    return np.ascontiguousarray(arr, dtype=np.float32)


def _dedup_keep_last(ids_arr: np.ndarray, vecs_arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Entfernt doppelte IDs, behält die *letzte* Vektorausprägung (Batch-stabil)."""
    seen: dict[int, int] = {}
    ids_list: List[int] = ids_arr.tolist()
    for i, aid in enumerate(ids_list):
        seen[int(aid)] = i  # letzter Index gewinnt
    keep_idx = np.array(sorted(seen.values()), dtype=np.int64)
    return ids_arr[keep_idx], vecs_arr[keep_idx, :]


# ────────────────────────────────────────────────────────────────────────────────
# Hauptfunktion: inkrementelle Updates
# ────────────────────────────────────────────────────────────────────────────────

def update_indices_after_import(
    app: FastAPI,
    session: Session,
    changed_abs_ids: Iterable[int] | None,
    changed_author_ids: Iterable[int] | None,
) -> None:
    """Aktualisiert Abstract- und Autoren-Indizes inkrementell.

    - Abstracts: Embeddings der geänderten IDs upserten (falls vorhanden).
    - Autor:innen: Mean-Embedding über verknüpfte Abstracts bilden, in DB persistieren,
      danach in FAISS upserten (oder bei None später entfernen — hier nur Upsert).

    Wichtig:
    - IDs als int64, Vektoren als float32 (2D, contiguous) vorbereiten.
    - Deduplizieren pro Batch, da FAISS eindeutige IDs erwartet.
    """

    changed_abs_ids = list({int(x) for x in (changed_abs_ids or [])})
    changed_author_ids = set(int(x) for x in (changed_author_ids or []))

    # Wenn Abstract-Embeddings geändert wurden, betroffene Autor:innen ergänzen
    if changed_abs_ids:
        rows = (
            session.query(AbstractAuthorLink.author_id)
            .filter(AbstractAuthorLink.abstract_id.in_(changed_abs_ids))
            .all()
        )
        for (aid,) in rows:
            changed_author_ids.add(int(aid))

        # -------- Abstracts upserten --------
        abs_rows = session.exec(select(Abstract).where(Abstract.id.in_(changed_abs_ids))).all()
        abs_ids: list[int] = []
        abs_vecs: list[np.ndarray] = []
        for a in abs_rows:
            if a.embedding:
                abs_ids.append(int(a.id))
                abs_vecs.append(np.asarray(a.embedding, dtype=np.float32))

        if abs_ids:
            ids_arr = np.asarray(abs_ids, dtype=np.int64)
            vecs_arr = _ensure_2d_contiguous(np.asarray(abs_vecs, dtype=np.float32))
            if len(ids_arr) != len(set(ids_arr.tolist())):
                ids_arr, vecs_arr = _dedup_keep_last(ids_arr, vecs_arr)

            # Optional: Lock verwenden, falls in app.state vorhanden
            lock = getattr(app.state, "faiss_lock", None)
            if lock:
                with lock:
                    app.state.indices.abs.add_or_update(ids_arr, vecs_arr)
            else:
                app.state.indices.abs.add_or_update(ids_arr, vecs_arr)
            logger.info("abstract-index upsert: %d items", len(ids_arr))

    # -------- Autoren: Mittelwert berechnen + persistieren + upserten --------
    up_author_ids: list[int] = []
    up_author_vecs: list[np.ndarray] = []

    for aid in changed_author_ids:
        mean_vec = _mean_author_embedding(session, aid)
        if mean_vec is None:
            continue
        author = session.get(Author, aid)
        if not author:
            continue
        f32_mean = mean_vec.astype(np.float32)
        author.embedding = f32_mean.tolist()
        up_author_ids.append(int(aid))
        up_author_vecs.append(f32_mean)

    if up_author_ids:
        # DB persistieren
        try:
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("commit failed in author embedding update")
            raise

        # In FAISS upserten (IDs zuerst!)
        ids_arr = np.asarray(up_author_ids, dtype=np.int64)
        vecs_arr = _ensure_2d_contiguous(np.asarray(up_author_vecs, dtype=np.float32))
        if len(ids_arr) != len(set(ids_arr.tolist())):
            ids_arr, vecs_arr = _dedup_keep_last(ids_arr, vecs_arr)

        lock = getattr(app.state, "faiss_lock", None)
        if lock:
            with lock:
                app.state.indices.auth.add_or_update(ids_arr, vecs_arr)
        else:
            app.state.indices.auth.add_or_update(ids_arr, vecs_arr)
        logger.info("author-index upsert: %d items", len(ids_arr))
