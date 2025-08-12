# app/api/routes_abstracts.py
from fastapi import APIRouter, Depends, Request, Query, UploadFile
from sqlmodel import Session
from typing import Optional
from app.db.base import get_session
from app.services.search_service import search_abstracts_service
from app.services.import_service import import_json_service
from app.models.domain import Abstract

router = APIRouter(tags=["abstracts"])

@router.get("/search")
async def search_abstracts(request: Request,
    keyword: str = Query("", description="Keyword; leer erlaubt"),
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
    topic_id: Optional[int] = Query(None),
    topic_ids: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    return await search_abstracts_service(request, session, keyword, page, page_size, topic_id, topic_ids)

@router.get("/{abstract_id}")
async def get_abstract_detail(abstract_id: int, session: Session = Depends(get_session)):
    obj = session.get(Abstract, abstract_id)
    if not obj:
        return {"error": "not_found", "id": abstract_id}
    return {
        "id": obj.id, "title": obj.title, "content_raw": obj.content_raw, "content": obj.content,
        "submission_date": obj.submission_date.isoformat() if obj.submission_date else None,
        "publication_date": obj.publication_date.isoformat() if obj.publication_date else None,
        "language_ref": obj.language_ref, "word_count": obj.word_count,
        "keywords": obj.keywords, "session_id": obj.session_id, "session_title": obj.session_title,
        "authors": [{"id": a.id, "name": a.name} for a in obj.authors],
        "topics": [{"id": t.id, "title": t.title} for t in obj.topics],
    }

@router.post("/import")
async def import_abstracts(request: Request, file: UploadFile, session: Session = Depends(get_session)):
    return await import_json_service(request, session, file)
