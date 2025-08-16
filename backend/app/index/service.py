"""\
app/index/service.py — Service-Layer für FAISS-Indizes

Ziele:
- Kapselt das Low-level-Handling (faiss_index.py) in eine einfache Service-API
- Bietet getrennte Services für Abstracts und Autor:innen (MultiIndex)
- Sorgt für konsistente Metrik-/Dim-Validierung und sichere Aufrufe
"""

from __future__ import annotations

# ── Standardbibliothek
import logging
import os
from typing import Iterable, Literal, Optional, Tuple

# ── Drittanbieter
import faiss  # type: ignore
import numpy as np
from sqlmodel import Session

# ── Lokale Module
from app.config import settings
from app.index import faiss_index as fx


# ────────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

Metric = Literal["ip", "l2"]


class IndexService:
    """Managed einen einzelnen FAISS-Index (IDMap2 über Flat-L2/IP).

    Hinweise:
    - `metric` steuert Normalisierung im Low-level (faiss_index):
      * "ip"  → L2-Normalisierung für Cosine-Äquivalent
      * "l2"  → euklidische Distanz
    - `index_path` definiert den Persistenzpfad des Index.
    """

    def __init__(self, dim: int, metric: Metric = "ip", index_path: Optional[str] = None) -> None:
        self.dim = int(dim)
        self.metric: Metric = metric
        self.index_path = index_path or os.path.join(settings.INDEX_DIR, "faiss.index")
        self.index: Optional[faiss.IndexIDMap2] = None

    # ────────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ────────────────────────────────────────────────────────────────────────────
    def load_or_build_abs(self, session: Session) -> None:
        """Lädt/erstellt den Abstract-Index; baut ihn aus der DB, wenn leer."""
        logger.debug("loading/creating abstracts index: dim=%d metric=%s path=%s", self.dim, self.metric, self.index_path)
        self.index = fx.load_or_create_index(self.dim, self.metric, self.index_path)
        if self.index.ntotal == 0:
            logger.info("abstracts index empty → building from DB")
            self.index = fx.build_abs_from_db(session, self.dim, self.metric, self.index)
            fx.save_index(self.index, self.index_path)
            logger.info("abstracts index built: ntotal=%d", self.index.ntotal)
        else:
            logger.debug("abstracts index loaded: ntotal=%d", self.index.ntotal)

    def load_or_build_auth(self, session: Session) -> None:
        """Lädt/erstellt den Author-Index; baut ihn aus der DB, wenn leer."""
        logger.debug("loading/creating authors index: dim=%d metric=%s path=%s", self.dim, self.metric, self.index_path)
        self.index = fx.load_or_create_index(self.dim, self.metric, self.index_path)
        if self.index.ntotal == 0:
            logger.info("authors index empty → building from DB")
            self.index = fx.build_auth_from_db(session, self.dim, self.metric, self.index)
            fx.save_index(self.index, self.index_path)
            logger.info("authors index built: ntotal=%d", self.index.ntotal)
        else:
            logger.debug("authors index loaded: ntotal=%d", self.index.ntotal)

    def save(self) -> None:
        """Persistiert den Index (no-op, wenn keiner geladen)."""
        if self.index is None:
            logger.debug("save() skipped: index not loaded")
            return
        fx.save_index(self.index, self.index_path)
        logger.debug("index saved: path=%s ntotal=%d", self.index_path, self.index.ntotal)

    # ────────────────────────────────────────────────────────────────────────────
    # Mutationen
    # ────────────────────────────────────────────────────────────────────────────
    def add_or_update(self, ids: Iterable[int] | np.ndarray, vecs: Iterable[Iterable[float]] | np.ndarray) -> None:
        """Upsertet Vektoren (remove+add) anhand der übergebenen IDs.

        Erwartet:
        - ids: iterable[int] oder np.ndarray[int64] der Länge N
        - vecs: iterable[iterable[float]] oder np.ndarray[float32] der Form (N, D)
        """
        if self.index is None:
            raise RuntimeError("Index not loaded — call load_or_build_* first")
        ids_arr = np.asarray(list(ids) if not isinstance(ids, np.ndarray) else ids, dtype=np.int64)
        vecs_arr = np.asarray(vecs, dtype=np.float32)
        if vecs_arr.ndim != 2:
            raise ValueError("vecs must be 2D [N, D]")
        if vecs_arr.shape[1] != self.dim:
            raise ValueError(f"vecs dimension {vecs_arr.shape[1]} != expected {self.dim}")
        logger.debug("upsert: n=%d dim=%d metric=%s", len(ids_arr), vecs_arr.shape[1], self.metric)
        fx.add_or_update(self.index, ids_arr, vecs_arr, metric=self.metric)

    def remove(self, ids: Iterable[int]) -> None:
        """Entfernt die angegebenen IDs aus dem Index (falls vorhanden)."""
        if self.index is None:
            raise RuntimeError("Index not loaded — call load_or_build_* first")
        ids_list = list(ids)
        logger.debug("remove: n=%d", len(ids_list))
        fx.remove_ids(self.index, ids_list)

    # ────────────────────────────────────────────────────────────────────────────
    # Suche
    # ────────────────────────────────────────────────────────────────────────────
    def search(self, q: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """Sucht Top-k Nachbarn für `q` (1D/2D erlaubt)."""
        if self.index is None:
            raise RuntimeError("Index not loaded — call load_or_build_* first")
        logger.debug("search: k=%d metric=%s qshape=%s", k, self.metric, getattr(q, "shape", None))
        return fx.search(self.index, q, k, metric=self.metric)


class MultiIndex:
    """Hält zwei getrennte IndexServices: Abstracts und Autor:innen."""

    def __init__(self, abs_index: IndexService, auth_index: IndexService) -> None:
        self.abs = abs_index
        self.auth = auth_index

    def load_or_build(self, session: Session) -> None:
        """Lädt oder baut beide Indizes aus der DB auf."""
        logger.debug("multi-index load_or_build start")
        self.abs.load_or_build_abs(session)
        self.auth.load_or_build_auth(session)
        logger.debug("multi-index load_or_build done: abs=%s auth=%s", getattr(self.abs.index, "ntotal", None), getattr(self.auth.index, "ntotal", None))

    def save(self) -> None:
        """Persistiert beide Indizes (no-op, wenn nicht geladen)."""
        logger.debug("multi-index save start")
        self.abs.save()
        self.auth.save()
        logger.debug("multi-index save done")
