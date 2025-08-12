from __future__ import annotations
from fastapi import Request
import threading
import app.index.faiss_index as faiss_index


def reindex_all_service(request: Request) -> dict:
    """
    Baut beide FAISS-Indizes aus der DB neu und tauscht sie atomar aus.
    """
    model = request.app.state.model
    lock: threading.RLock | None = getattr(request.app.state, "faiss_lock", None)

    abstract_idx, author_idx = faiss_index.build_indices(model)

    # atomarer Swap
    if lock:
        with lock:
            request.app.state.abstract_index = abstract_idx
            request.app.state.author_index = author_idx
            faiss_index.abstract_index = abstract_idx
            faiss_index.author_index = author_idx
    else:
        request.app.state.abstract_index = abstract_idx
        request.app.state.author_index = author_idx
        faiss_index.abstract_index = abstract_idx
        faiss_index.author_index = author_idx

    return {
        "status": "ok",
        "indices": {
            "abstracts": int(getattr(abstract_idx, "ntotal", 0) or 0),
            "authors": int(getattr(author_idx, "ntotal", 0) or 0),
        },
    }
