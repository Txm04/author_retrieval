"""\
app/api/routes_topics.py — API-Routen für Topics

Ziele:
- Endpoint zum Auflisten aller Topics inkl. Anzahl verknüpfter Abstracts
- Verwendung von FastAPI-Dependency `get_session` für DB-Zugriff
"""

from __future__ import annotations

# ── Standardbibliothek
import logging
from typing import Any, Dict, List

# ── Drittanbieter
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

# ── Lokale Module
from app.db.base import get_session
from app.models.domain import Topic, Abstract  # Abstract nur für das COUNT-Join


# ----------------------------------------------------------------------------
# Logger
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Router-Definition
# ----------------------------------------------------------------------------
router = APIRouter(tags=["topics"])  # Tag erscheint in der OpenAPI-Doku


# ----------------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------------
@router.get("/topics")
async def list_topics(session: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    """Liefert alle Topics inkl. Anzahl verknüpfter Abstracts.

    Rückgabeformat (Liste von Objekten):
      - id: int — Primärschlüssel des Topics
      - title: str — Titel des Topics
      - abstract_count: int — Anzahl verknüpfter Abstracts
    """
    logger.info("GET /topics")

    # Aggregation über die Relationship `Topic.abstracts` (LEFT OUTER JOIN, damit Topics ohne Abstracts
    # als 0 gezählt werden). Diese Variante vermeidet N+1-Zugriffe (im Vergleich zu len(t.abstracts)).
    stmt = (
        select(
            Topic.id.label("id"),
            Topic.title.label("title"),
            func.count(Abstract.id).label("abstract_count"),
        )
        .select_from(Topic)
        .join(Topic.abstracts, isouter=True)
        .group_by(Topic.id, Topic.title)
        .order_by(Topic.title.asc())
    )

    try:
        rows = session.exec(stmt).all()
    except Exception:
        logger.exception("GET /topics: DB-Fehler beim Laden der Topics")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="topics_query_failed")

    # rows ist eine Liste von Tupeln/Row-Objekten entsprechend der select-Reihenfolge
    result: List[Dict[str, Any]] = [
        {"id": r.id, "title": r.title, "abstract_count": int(r.abstract_count or 0)}
        for r in rows
    ]

    logger.debug("GET /topics: %s Topics geliefert", len(result))
    return result
