# app/api/routes_topics.py
from fastapi import APIRouter, Depends, Request, Query
from sqlmodel import Session
from app.db.base import get_session
from app.models.domain import Topic

router = APIRouter()

@router.get("/topics")
async def list_topics(session: Session = Depends(get_session)):
    rows = session.query(Topic).all()
    return [
        {"id": t.id, "title": t.title, "abstract_count": len(t.abstracts)}
        for t in rows
    ]