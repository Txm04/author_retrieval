"""\
app/index/faiss_index.py — Low-level FAISS-Hilfsfunktionen

Aufgaben dieses Moduls:
- Index laden/speichern (IDMap2 um Flat-L2/IP)
- Index aus der DB aufbauen (Abstracts/Authors)
- Mutationen (add_or_update, remove_ids)
- Suche (Top-k, optional IP-Normalisierung)

Hinweise:
- Normalisierung für Cosine-Äquivalent geschieht nur bei metric="ip".
- Vektoren werden konsequent als float32, contiguous gehalten.
"""

from __future__ import annotations

# ── Standardbibliothek
import logging
import os
from typing import Iterable, Literal, Optional, Tuple

# ── Drittanbieter
import faiss  # type: ignore
import numpy as np
from sqlmodel import Session, select

# ── Lokale Module
from app.models.domain import Abstract, Author


# ────────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ────────────────────────────────────────────────────────────────────────────────
Metric = Literal["ip", "l2"]


def _to_f32(a: np.ndarray) -> np.ndarray:
    """Sorge für float32 + contiguous Layout (FAISS erwartet das)."""
    return np.ascontiguousarray(a.astype(np.float32, copy=False))


def _normalize_if_ip(x: np.ndarray, metric: Metric) -> None:
    """In-place L2-Normalisierung, wenn mit Inner Product (cosine) gesucht/gebaut wird."""
    if metric == "ip" and x.size:
        faiss.normalize_L2(x)


def _validate_metric(metric: str) -> Metric:
    if metric not in ("ip", "l2"):
        raise ValueError("metric must be 'ip' or 'l2'")
    return metric  # type: ignore[return-value]


def _make_base_index(dim: int, metric: Metric) -> faiss.Index:
    return faiss.IndexFlatIP(dim) if metric == "ip" else faiss.IndexFlatL2(dim)


# ────────────────────────────────────────────────────────────────────────────────
# Lifecycle
# ────────────────────────────────────────────────────────────────────────────────

def load_or_create_index(dim: int, metric: str, index_path: str) -> faiss.IndexIDMap2:
    """Lädt einen FAISS-Index oder erstellt einen neuen IDMap2-Wrapper über Flat.

    Regeln beim Laden:
    - Wenn Datei existiert und bereits ein IndexIDMap2 ist → zurückgeben.
    - Wenn Datei existiert, aber kein IDMap2 ist:
        * wenn ntotal == 0 → in IDMap2 wrappen
        * wenn ntotal  > 0 → Datei ignorieren (legacy) und leeren Index neu erstellen
    - Wenn Datei nicht existiert → neuen leeren Index erstellen.
    """
    m = _validate_metric(metric)
    logger.debug("load_or_create_index: dim=%d metric=%s path=%s", dim, m, index_path)

    if index_path and os.path.exists(index_path):
        idx = faiss.read_index(index_path)
        if isinstance(idx, faiss.IndexIDMap2):
            logger.debug("index loaded (IDMap2): ntotal=%d", idx.ntotal)
            return idx
        if idx.ntotal == 0:
            logger.debug("legacy index (empty) → wrap into IDMap2")
            return faiss.IndexIDMap2(idx)
        # gefüllt, aber falscher Typ → Datei verwerfen und neu erstellen
        try:
            os.remove(index_path)
            logger.warning("removed legacy index with items (wrong type): path=%s", index_path)
        except Exception:
            logger.exception("failed to remove legacy index: path=%s", index_path)
        base = _make_base_index(dim, m)
        new_idx = faiss.IndexIDMap2(base)
        logger.debug("created fresh IDMap2 after legacy removal")
        return new_idx

    base = _make_base_index(dim, m)
    new_idx = faiss.IndexIDMap2(base)
    logger.debug("created new empty IDMap2 index")
    return new_idx


def save_index(index: faiss.IndexIDMap2, index_path: str) -> None:
    """Persistiert den Index, wenn ein Pfad angegeben ist."""
    if not index_path:
        logger.debug("save_index skipped: empty path")
        return
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_path)
    logger.debug("index saved: path=%s ntotal=%d", index_path, getattr(index, "ntotal", -1))


def build_abs_from_db(
    session: Session,
    dim: int,
    metric: str,
    index: Optional[faiss.IndexIDMap2] = None,
) -> faiss.IndexIDMap2:
    """Erzeugt/füllt den Abstract-Index aus DB-Embeddings.

    Achtung: prüft, ob Embedding-Dimensionen zum Index passen.
    """
    m = _validate_metric(metric)
    idx = index or load_or_create_index(dim, m, "")

    rows = session.exec(
        select(Abstract.id, Abstract.embedding).where(Abstract.embedding.is_not(None))
    ).all()
    if not rows:
        logger.info("build_abs_from_db: no rows with embeddings found")
        return idx

    ids = np.array([r[0] for r in rows], dtype=np.int64)
    vecs = _to_f32(np.vstack([r[1] for r in rows]))
    if vecs.shape[1] != dim:
        logger.error("Abstract embedding dimension mismatch: got=%d expected=%d", vecs.shape[1], dim)
        raise RuntimeError(f"Abstract embedding dimension {vecs.shape[1]} != expected {dim}")
    _normalize_if_ip(vecs, m)

    idx.add_with_ids(vecs, ids)
    logger.info("build_abs_from_db: added=%d ntotal=%d", len(ids), idx.ntotal)
    return idx


def build_auth_from_db(
    session: Session,
    dim: int,
    metric: str,
    index: Optional[faiss.IndexIDMap2] = None,
) -> faiss.IndexIDMap2:
    """Erzeugt/füllt den Author-Index aus DB-Embeddings.

    Achtung: prüft, ob Embedding-Dimensionen zum Index passen.
    """
    m = _validate_metric(metric)
    idx = index or load_or_create_index(dim, m, "")

    rows = session.exec(
        select(Author.id, Author.embedding).where(Author.embedding.is_not(None))
    ).all()
    if not rows:
        logger.info("build_auth_from_db: no rows with embeddings found")
        return idx

    ids = np.array([r[0] for r in rows], dtype=np.int64)
    vecs = _to_f32(np.vstack([r[1] for r in rows]))
    if vecs.shape[1] != dim:
        logger.error("Author embedding dimension mismatch: got=%d expected=%d", vecs.shape[1], dim)
        raise RuntimeError(f"Author embedding dimension {vecs.shape[1]} != expected {dim}")
    _normalize_if_ip(vecs, m)

    idx.add_with_ids(vecs, ids)
    logger.info("build_auth_from_db: added=%d ntotal=%d", len(ids), idx.ntotal)
    return idx


# ────────────────────────────────────────────────────────────────────────────────
# Mutationen
# ────────────────────────────────────────────────────────────────────────────────

def add_or_update(
    index: faiss.IndexIDMap2, ids: np.ndarray, vecs: np.ndarray, metric: str = "ip"
) -> None:
    """Upsert (remove + add) für Flat-Indizes.

    Erwartet:
    - ids: int64 Array (N,)
    - vecs: float32 Array (N, D)
    - metric: 'ip' → Normalisierung, 'l2' → keine
    """
    m = _validate_metric(metric)
    ids = np.asarray(ids, dtype=np.int64)
    vecs = _to_f32(vecs)
    if vecs.ndim != 2:
        raise ValueError("vecs must be a 2D array [N, D]")
    _normalize_if_ip(vecs, m)

    if hasattr(index, "remove_ids"):
        index.remove_ids(faiss.IDSelectorBatch(ids))
    index.add_with_ids(vecs, ids)
    logger.debug("add_or_update: upserted=%d ntotal=%d", len(ids), index.ntotal)


def remove_ids(index: faiss.IndexIDMap2, ids: Iterable[int]) -> None:
    """Entfernt eine Menge von IDs aus dem Index (falls vorhanden)."""
    arr = np.asarray(list(ids), dtype=np.int64)
    if arr.size:
        index.remove_ids(faiss.IDSelectorBatch(arr))
        logger.debug("remove_ids: removed=%d ntotal=%d", arr.size, index.ntotal)
    else:
        logger.debug("remove_ids: nothing to remove")


# ────────────────────────────────────────────────────────────────────────────────
# Suche
# ────────────────────────────────────────────────────────────────────────────────

def search(
    index: faiss.IndexIDMap2, q: np.ndarray, k: int = 10, metric: str = "ip"
) -> Tuple[np.ndarray, np.ndarray]:
    """Sucht Top-k Nachbarn für die Query-Vektoren.

    Returns:
        (D, I): Distanzen/Scores und korrespondierende IDs, jeweils (N, k)
    """
    m = _validate_metric(metric)
    q = _to_f32(q)
    if q.ndim == 1:
        q = q.reshape(1, -1)
    _normalize_if_ip(q, m)
    D, I = index.search(q, k)
    logger.debug("search: n_queries=%d k=%d", q.shape[0], k)
    return D, I
