# app/api/routes_admin.py
from fastapi import APIRouter, Request, Body, Depends
from sqlmodel import Session
from sqlalchemy import func
import torch
from app.db.base import get_session
from app.embeddings.encoder import load_model
from app.index.faiss_index import build_indices
import app.index.faiss_index as faiss_index
from app.models.domain import Abstract, Author

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/status")
async def admin_status(request: Request, session: Session = Depends(get_session)):
    abstract_count = session.query(func.count(Abstract.id)).scalar() or 0
    author_count = session.query(func.count(Author.id)).scalar() or 0
    aidx = getattr(request.app.state, "abstract_index", None)
    auidx = getattr(request.app.state, "author_index", None)
    return {
        "model": {
            "name": getattr(request.app.state, "model_name", "unknown"),
            "device": getattr(request.app.state, "model_device", "cpu"),
            "available": {"cpu": True, "cuda": torch.cuda.is_available(), "mps": torch.backends.mps.is_available()}
        },
        "counts": {"abstracts": int(abstract_count), "authors": int(author_count)},
        "indices": {"abstracts": int(getattr(aidx, "ntotal", 0) or 0), "authors": int(getattr(auidx, "ntotal", 0) or 0)},
        "config": {
            "show_scores": bool(getattr(request.app.state, "show_scores", False)),
            "score_mode": getattr(request.app.state, "score_mode", "cosine"),
        }
    }

@router.post("/config")
async def admin_config(request: Request, payload: dict = Body(...)):
    device = payload.get("device")
    if device:
      import torch
      if device == "cuda" and not torch.cuda.is_available(): return {"error":"cuda_unavailable"}
      if device == "mps" and not torch.backends.mps.is_available(): return {"error":"mps_unavailable"}
      model_name = getattr(request.app.state, "model_name", "all-MiniLM-L6-v2")
      model, actual = load_model(model_name=model_name, device=device)
      request.app.state.model = model
      request.app.state.model_device = actual
    if "show_scores" in payload: request.app.state.show_scores = bool(payload["show_scores"])
    if payload.get("score_mode") in ("cosine","faiss"): request.app.state.score_mode = payload["score_mode"]
    return {
        "status": "ok",
        "model": {"name": getattr(request.app.state,"model_name",""), "device": getattr(request.app.state,"model_device","")},
        "config": {"show_scores": bool(getattr(request.app.state,"show_scores",False)),
                   "score_mode": getattr(request.app.state,"score_mode","cosine")}
    }

@router.post("/reindex")
async def admin_reindex(request: Request):
    abstract_idx, author_idx = build_indices(request.app.state.model)

    lock = getattr(request.app.state, "faiss_lock", None)
    if lock:
        with lock:
            request.app.state.abstract_index = abstract_idx
            request.app.state.author_index = author_idx
    else:
        request.app.state.abstract_index = abstract_idx
        request.app.state.author_index = author_idx

    return {
        "status": "ok",
        "indices": {
            "abstracts": int(getattr(abstract_idx, "ntotal", 0) or 0),
            "authors": int(getattr(author_idx, "ntotal", 0) or 0),
        },
    }
