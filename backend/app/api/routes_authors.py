# app/api/routes_authors.py
from fastapi import APIRouter, Depends, Request, Query
from sqlmodel import Session
from app.db.base import get_session
from app.models.domain import Abstract, AbstractAuthorLink, Author
from app.services.search_service import search_authors_service, similar_authors_service
from sqlalchemy.orm import selectinload
from typing import List
router = APIRouter(tags=["authors"])

@router.get("/search")
async def search_authors(request: Request,
    keyword: str = Query(..., description="Suchbegriff"),
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
    session: Session = Depends(get_session),
):
    return await search_authors_service(request, session, keyword, page, page_size)

@router.get("/{author_id}")
async def get_author_detail(author_id: int, session: Session = Depends(get_session)):
    author = session.get(Author, author_id)
    if not author:
        return {"error": "not_found", "id": author_id}

    abs_rows: List[Abstract] = (
        session.query(Abstract)
        .options(selectinload(Abstract.topics))
        .join(AbstractAuthorLink, AbstractAuthorLink.abstract_id == Abstract.id)
        .filter(AbstractAuthorLink.author_id == author_id)
        .order_by(Abstract.publication_date.desc().nullslast(), Abstract.id.desc())
        .all()
    )

    return {
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

@router.get("/{author_id}/similar")
async def get_similar_authors(request: Request, author_id: int, top_k: int = 5, session: Session = Depends(get_session)):
    return await similar_authors_service(request, session, author_id, top_k)
