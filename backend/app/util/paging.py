"""
app/util/paging.py — Hilfsfunktionen für Pagination

Ziele:
- Einheitliche Normalisierung von page und page_size
- Verhindert negative/ungültige Werte
- Liefert Offset-Berechnung für SQL-Queries
"""

import logging

# ────────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


def clamp_page(page: int) -> int:
    """Sorgt dafür, dass page >= 1 ist."""
    try:
        p = int(page)
    except (TypeError, ValueError):
        logger.warning("Ungültiger page-Wert %r, fallback=1", page)
        return 1
    return max(1, p)


def clamp_page_size(n: int, lo: int = 1, hi: int = 100) -> int:
    """
    Normalisiert page_size in das Intervall [lo, hi].
    Default: 1 ≤ page_size ≤ 100.
    """
    try:
        size = int(n)
    except (TypeError, ValueError):
        logger.warning("Ungültiger page_size-Wert %r, fallback=%d", n, lo)
        return lo
    return max(lo, min(hi, size))


def offset_for(page: int, page_size: int) -> int:
    """
    Liefert SQL-kompatiblen Offset für die Pagination.
    Beispiel: page=1 -> 0, page=2, page_size=10 -> 10.
    """
    return (page - 1) * page_size
