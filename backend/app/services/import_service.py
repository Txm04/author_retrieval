from __future__ import annotations
from typing import Iterable
import json
import numpy as np
import faiss

from fastapi import Request, UploadFile
from sqlmodel import Session

from app.models.domain import (
    Abstract, Author, Topic,
    AbstractAuthorLink, AbstractTopicLink
)
from app.embeddings.encoder import encode_texts
from app.index.faiss_index import VECTOR_DIM
import app.index.faiss_index as faiss_index


def _safe_str(x: str | None) -> str:
    return x or ""


async def import_json_service(
    request: Request,
    session: Session,
    file: UploadFile,
) -> dict:
    """
    Liest die JSON-Datei, importiert Abstracts/Autoren/Topics inkl. Linktabellen
    (duplizierende Einträge werden dedupliziert), erzeugt Embeddings für neue
    Abstracts und aktualisiert FAISS (Abstract + Autoren).
    """
    raw = await file.read()
    try:
        data = json.loads(raw)
        assert isinstance(data, list)
    except Exception:
        return {"error": "invalid_json"}

    texts: list[str] = []
    new_abstracts: list[Abstract] = []
    abstract_author_links: list[AbstractAuthorLink] = []

    seen_in_file: set[tuple[int, int | None]] = set()  # (abstract_id, topic_id)
    links_seen: set[tuple[int, int]] = set()          # (abstract_id, author_id)
    affected_author_ids: set[int] = set()

    for item in data:
        abstract_id = int(item["id"])
        topic_id = item.get("topic_id")
        key_in_file = (abstract_id, topic_id)
        if key_in_file in seen_in_file:
            # Mehrfaches (Abstract,Topic) im Importfile überspringen
            continue
        seen_in_file.add(key_in_file)

        # Abstract (Upsert: nur anlegen, wenn nicht vorhanden)
        abs_obj = session.get(Abstract, abstract_id)
        if not abs_obj:
            abs_obj = Abstract(
                id=abstract_id,
                title=_safe_str(item.get("title")),
                content_raw=_safe_str(item.get("content_raw")),
                content=item.get("content"),
                submission_date=item.get("submission_date"),
                publication_date=item.get("publication_date"),
                language_ref=item.get("language_ref"),
                word_count=item.get("word_count"),
                keywords=item.get("keywords"),
                session_id=item.get("session_id"),
                session_title=item.get("session_title"),
            )
            session.add(abs_obj)
            new_abstracts.append(abs_obj)
            texts.append(f"{_safe_str(abs_obj.title)}. {_safe_str(abs_obj.content_raw)}")

        # Autoren + Links (dedupe)
        for auth_data in item.get("authors", []) or []:
            author_id = auth_data.get("author_id")
            if author_id is None:
                continue
            author_id = int(author_id)

            author = session.get(Author, author_id)
            if not author:
                # Fallback: academicdegree als Name, falls echte Namen fehlen
                author_name = (auth_data.get("academicdegree") or "Unknown").strip()
                author = Author(id=author_id, name=author_name)
                session.add(author)

            link_key = (abs_obj.id, author.id)
            if link_key in links_seen:
                continue
            links_seen.add(link_key)

            # Datenbank-Dedupe
            exists = (
                session.query(AbstractAuthorLink)
                .filter_by(abstract_id=abs_obj.id, author_id=author.id)
                .first()
            )
            if not exists:
                abstract_author_links.append(
                    AbstractAuthorLink(abstract_id=abs_obj.id, author_id=author.id)
                )
                affected_author_ids.add(author.id)

        # Topics + Link
        t_id = item.get("topic_id")
        t_title = item.get("topic_title")
        if t_id is not None and t_title:
            t_id = int(t_id)
            topic = session.get(Topic, t_id)
            if not topic:
                topic = Topic(id=t_id, title=str(t_title))
                session.add(topic)

            link_exists = (
                session.query(AbstractTopicLink)
                .filter_by(abstract_id=abs_obj.id, topic_id=topic.id)
                .first()
            )
            if not link_exists:
                session.add(AbstractTopicLink(abstract_id=abs_obj.id, topic_id=topic.id))

    if abstract_author_links:
        session.add_all(abstract_author_links)

    # ---- Commit DB-Struktur, BEVOR Embeddings erzeugt werden
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    # ---- Embeddings/FAISS für neue Abstracts
    added_abstracts = 0
    if new_abstracts:
        model = request.app.state.model
        vecs = np.asarray(encode_texts(model, texts), dtype=np.float32)
        ids = np.asarray([a.id for a in new_abstracts], dtype=np.int64)

        for abs_obj, vec in zip(new_abstracts, vecs):
            abs_obj.embedding = vec.tolist()

        try:
            session.commit()
        except Exception:
            session.rollback()
            raise

        # Index anlegen (falls None) + hinzufügen unter Lock
        index = getattr(request.app.state, "abstract_index", None)
        if index is None:
            index = faiss.IndexIDMap(faiss.IndexFlatL2(VECTOR_DIM))
            request.app.state.abstract_index = index
            faiss_index.abstract_index = index

        lock = getattr(request.app.state, "faiss_lock", None)
        if lock:
            with lock:
                index.add_with_ids(vecs, ids)
        else:
            index.add_with_ids(vecs, ids)

        added_abstracts = len(new_abstracts)

    # ---- Autoren-Embeddings (Mean über deren Abstract-Embeddings) & FAISS-Upsert
    upserted_authors = _recompute_and_upsert_author_vectors(
        request=request,
        session=session,
        author_ids=affected_author_ids,
    )

    return {
        "status": "imported",
        "count": added_abstracts,
        "authors_updated": upserted_authors,
    }


def _recompute_and_upsert_author_vectors(
    request: Request,
    session: Session,
    author_ids: Iterable[int],
) -> int:
    """
    Berechnet für gegebene Autoren die Mean-Embeddings und upsertet sie in den
    Author-FAISS-Index (remove_ids + add_with_ids).
    """
    author_ids = list(set(int(a) for a in author_ids))
    if not author_ids:
        return 0

    from app.models.domain import Abstract, AbstractAuthorLink, Author

    author_idx = getattr(request.app.state, "author_index", None)
    if author_idx is None:
        author_idx = faiss.IndexIDMap(faiss.IndexFlatL2(VECTOR_DIM))
        request.app.state.author_index = author_idx
        faiss_index.author_index = author_idx

    updated = 0
    lock = getattr(request.app.state, "faiss_lock", None)

    author_vecs: list[np.ndarray] = []
    author_ids_arr: list[int] = []

    for aid in author_ids:
        abs_list: list[Abstract] = (
            session.query(Abstract)
            .join(AbstractAuthorLink, AbstractAuthorLink.abstract_id == Abstract.id)
            .filter(
                AbstractAuthorLink.author_id == aid,
                Abstract.embedding != None
            )
            .all()
        )
        if not abs_list:
            continue

        vecs = np.array([a.embedding for a in abs_list], dtype=np.float32)
        mean_vec = np.mean(vecs, axis=0)

        author = session.get(Author, aid)
        if not author:
            continue
        author.embedding = mean_vec.tolist()
        author_vecs.append(mean_vec.astype(np.float32))
        author_ids_arr.append(aid)
        updated += 1

    if author_vecs:
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise

        ids_arr = np.asarray(author_ids_arr, dtype=np.int64)
        vec_arr = np.asarray(author_vecs, dtype=np.float32)

        if lock:
            with lock:
                _upsert_in_index(request.app.state.author_index, vec_arr, ids_arr)
        else:
            _upsert_in_index(request.app.state.author_index, vec_arr, ids_arr)

    return updated


def _upsert_in_index(index: faiss.IndexIDMap, vecs: np.ndarray, ids: np.ndarray) -> None:
    """
    Entfernt vorhandene IDs (falls vorhanden) und fügt neue Vektoren hinzu.
    """
    try:
        index.remove_ids(ids)
    except Exception:
        # remove_ids kann je nach Index-Implementierung Fehler werfen, wenn ID nicht existiert
        pass
    index.add_with_ids(vecs, ids)
