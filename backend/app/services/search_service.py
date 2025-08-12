from __future__ import annotations
from typing import Optional
import numpy as np

from fastapi import Request
from sqlmodel import Session

from app.embeddings.encoder import encode_texts
from app.models.domain import Abstract, Author, AbstractTopicLink, Topic
from app.util.scoring import cosine, faiss_score_from_l2
from app.config import settings


# ---------------------------
# Abstract-Suche (mit Topics)
# ---------------------------
async def search_abstracts_service(
    request: Request,
    session: Session,
    keyword: str,
    page: int,
    page_size: int,
    topic_id: Optional[int],
    topic_ids: Optional[str],
) -> dict:
    show_scores: bool = bool(getattr(request.app.state, "show_scores", False))
    score_mode: str = getattr(request.app.state, "score_mode", "cosine")  # "cosine"|"faiss"

    index = getattr(request.app.state, "abstract_index", None)
    lock = getattr(request.app.state, "faiss_lock", None)
    model = request.app.state.model

    # Topic-Filter vorbereiten
    ids_prefilter: Optional[set[int]] = None
    if topic_id is not None or topic_ids:
        ids_list: list[int] = []
        if topic_id is not None:
            ids_list.append(int(topic_id))
        if topic_ids:
            ids_list.extend(
                [int(x) for x in topic_ids.split(",") if x.strip().isdigit()]
            )
        ids_list = list({*ids_list})
        if ids_list:
            rows = (
                session.query(AbstractTopicLink.abstract_id)
                .filter(AbstractTopicLink.topic_id.in_(ids_list))
                .all()
            )
            ids_prefilter = {r[0] for r in rows}
            if not ids_prefilter:
                return {"query": keyword, "page": page, "page_size": page_size, "results": []}

    # Nur Topic-Filter (kein Keyword) -> DB-Query ohne Scores
    if (keyword or "").strip() == "" and ids_prefilter is not None:
        offset = (page - 1) * page_size
        rows = (
            session.query(Abstract)
            .filter(Abstract.id.in_(ids_prefilter))
            .order_by(Abstract.publication_date.desc().nullslast(), Abstract.id.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        ids_this_page = [r.id for r in rows]
        link_rows = (
            session.query(AbstractTopicLink.abstract_id, Topic.title)
            .join(Topic, Topic.id == AbstractTopicLink.topic_id)
            .filter(AbstractTopicLink.abstract_id.in_(ids_this_page))
            .all()
        )
        topics_map = {}
        for aid, ttitle in link_rows:
            topics_map.setdefault(aid, []).append(ttitle)

        return {
            "query": keyword,
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "id": r.id,
                    "title": r.title,
                    "session_title": r.session_title,
                    "topic_title": (topics_map.get(r.id, [None]) or [None])[0],
                }
                for r in rows
            ],
        }

    # FAISS-Route
    if index is None:
        return {"error": "FAISS index not initialized"}

    vec = encode_texts(model, [keyword or ""])[0]
    q = np.ascontiguousarray(vec[None, :], dtype=np.float32)

    want = page * page_size
    oversample = max(want * settings.INDEX_OVERSAMPLE_FACTOR, want)

    if lock:
        with lock:
            D, I = index.search(q, oversample)
    else:
        D, I = index.search(q, oversample)

    faiss_ids = [int(x) for x in I[0] if x != -1]
    faiss_D = [float(d) for d in D[0][:len(faiss_ids)]]

    if ids_prefilter is not None:
        paired = [(i, d) for i, d in zip(faiss_ids, faiss_D) if i in ids_prefilter]
        if not paired:
            return {"query": keyword, "page": page, "page_size": page_size, "results": []}
        faiss_ids, faiss_D = (list(t) for t in zip(*paired))

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    page_ids = faiss_ids[start:end]
    page_D = faiss_D[start:end]

    if not page_ids:
        return {"query": keyword, "page": page, "page_size": page_size, "results": []}

    rows = session.query(Abstract).filter(Abstract.id.in_(page_ids)).all()
    order = {v: i for i, v in enumerate(page_ids)}
    rows.sort(key=lambda r: order.get(r.id, 10**9))

    link_rows = (
        session.query(AbstractTopicLink.abstract_id, Topic.title)
        .join(Topic, Topic.id == AbstractTopicLink.topic_id)
        .filter(AbstractTopicLink.abstract_id.in_(page_ids))
        .all()
    )
    topics_map: dict[int, list[str]] = {}
    for aid, ttitle in link_rows:
        topics_map.setdefault(aid, []).append(ttitle)

    # Scores (optional)
    scores_map: dict[int, float] = {}
    if show_scores and (keyword or "").strip():
        if score_mode == "faiss":
            for aid, d in zip(page_ids, page_D):
                scores_map[aid] = faiss_score_from_l2(d)
        else:
            q_vec = q[0]
            for r in rows:
                if r.embedding:
                    scores_map[r.id] = float(cosine(q_vec, np.asarray(r.embedding, dtype=np.float32)))

    return {
        "query": keyword,
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "id": r.id,
                "title": r.title,
                "session_title": r.session_title,
                "topic_title": (topics_map.get(r.id, [None]) or [None])[0],
                **({"score": round(scores_map.get(r.id, 0.0), 4)}
                   if show_scores and (keyword or "").strip() else {}),
            }
            for r in rows
        ],
    }


# -------------------------
# Autoren-Suche (FAISS)
# -------------------------
async def search_authors_service(
    request: Request,
    session: Session,
    keyword: str,
    page: int,
    page_size: int,
) -> dict:
    show_scores: bool = bool(getattr(request.app.state, "show_scores", False))
    score_mode: str = getattr(request.app.state, "score_mode", "cosine")

    author_index = getattr(request.app.state, "author_index", None)
    if author_index is None or getattr(author_index, "ntotal", 0) == 0:
        return {"query": keyword, "page": page, "page_size": page_size, "results": []}

    model = request.app.state.model
    vec = encode_texts(model, [keyword])[0].astype(np.float32)

    want = page * page_size
    oversample = max(want * settings.INDEX_OVERSAMPLE_FACTOR, want)
    D, I = author_index.search(vec[None, :], oversample)

    pairs = [(int(i), float(d)) for i, d in zip(I[0].tolist(), D[0].tolist()) if int(i) != -1]
    if not pairs:
        return {"query": keyword, "page": page, "page_size": page_size, "results": []}

    start = (page - 1) * page_size
    end = start + page_size
    page_pairs = pairs[start:end]
    if not page_pairs:
        return {"query": keyword, "page": page, "page_size": page_size, "results": []}

    page_ids = [i for i, _ in page_pairs]
    page_dists = {i: d for i, d in page_pairs}

    rows = session.query(Author).filter(Author.id.in_(page_ids)).all()
    order = {v: i for i, v in enumerate(page_ids)}
    rows.sort(key=lambda a: order.get(a.id, 10**9))

    scores_map: dict[int, float] = {}
    if show_scores:
        if score_mode == "faiss":
            for aid in page_ids:
                scores_map[aid] = faiss_score_from_l2(page_dists.get(aid, 0.0))
        else:
            qn = float(np.linalg.norm(vec))
            for a in rows:
                if not a.embedding:
                    continue
                av = np.asarray(a.embedding, dtype=np.float32)
                an = float(np.linalg.norm(av))
                if qn == 0.0 or an == 0.0:
                    score = 0.0
                else:
                    score = float(np.dot(vec, av) / (qn * an))
                scores_map[a.id] = score

    return {
        "query": keyword,
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "id": a.id,
                "name": a.name,
                "abstract_count": len(a.abstracts),
                **({"score": round(scores_map.get(a.id, 0.0), 4)} if show_scores and a.id in scores_map else {}),
            }
            for a in rows
        ],
    }


# -------------------------
# Ähnliche Autoren
# -------------------------
async def similar_authors_service(
    request: Request,
    session: Session,
    author_id: int,
    top_k: int,
) -> dict:
    show_scores: bool = bool(getattr(request.app.state, "show_scores", False))
    score_mode: str = getattr(request.app.state, "score_mode", "cosine")

    author = session.get(Author, author_id)
    if not author or not author.embedding:
        return {"id": author_id, "results": []}

    index = getattr(request.app.state, "author_index", None)
    if index is None or getattr(index, "ntotal", 0) == 0:
        return {"id": author_id, "results": []}

    q_vec = np.asarray(author.embedding, dtype=np.float32)
    D, I = index.search(q_vec[None, :], top_k + 1)  # +1: eigener Autor

    raw_ids = [int(x) for x in I[0] if x != -1]
    raw_D = [float(d) for d in D[0][:len(raw_ids)]]
    pairs = [(i, d) for i, d in zip(raw_ids, raw_D) if i != author_id]
    if not pairs:
        return {"id": author_id, "results": []}

    ids = [i for i, _ in pairs]
    dists = {i: d for i, d in pairs}

    others = session.query(Author).filter(Author.id.in_(ids)).all()
    order = {v: i for i, v in enumerate(ids)}
    others.sort(key=lambda r: order.get(r.id, 10**9))

    scores_map: dict[int, float] = {}
    if show_scores:
        if score_mode == "faiss":
            scores_map = {aid: faiss_score_from_l2(dists.get(aid, 0.0)) for aid in ids}
        else:
            for a in others:
                if a.embedding:
                    scores_map[a.id] = float(cosine(q_vec, np.asarray(a.embedding, dtype=np.float32)))

    return {
        "id": author_id,
        "results": [
            {
                "id": a.id,
                "name": a.name,
                **({"score": round(scores_map.get(a.id, 0.0), 4)} if show_scores else {}),
            }
            for a in others
        ],
    }
