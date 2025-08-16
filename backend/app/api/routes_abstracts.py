"""\
app/api/routes_abstracts.py — Routen für Abstract-Suche, Detail, Import, Patch & Delete

Ziele:
- /abstracts/search    → Paginierte Suche (optional nach Topic gefiltert)
- /abstracts/{id}      → Detailansicht inkl. Autoren & Topics
- /abstracts/import    → JSON-Import (delegiert an Service)
- /abstracts/{id} PATCH→ Felder aktualisieren, Topics pflegen, optional Re-Embedding + Index-Update
- /abstracts/{id} DEL  → Abstract löschen, abh. Author-Embeddings aktualisieren, Indizes bereinigen
"""
from __future__ import annotations

# ── Standardbibliothek
import logging
from datetime import datetime
from typing import Any, Dict, Optional

# ── Drittanbieter
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, UploadFile, status
from sqlmodel import Session, select

# ── Lokale Module
from app.db.base import get_session
from app.embeddings.encoder import encode_texts
from app.models.domain import (
    Abstract,
    AbstractAuthorLink,
    AbstractTopicLink,
    Author,
    Topic,
)
from app.services.import_service import import_json_service
from app.services.search_service import search_abstracts_service


# ----------------------------------------------------------------------------
# Logger
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


router = APIRouter(tags=["abstracts"])


# ────────────────────────────────────────────────────────────────────────────────
# SEARCH & DETAIL & IMPORT
# ────────────────────────────────────────────────────────────────────────────────
@router.get("/search")
async def search_abstracts(
    request: Request,
    keyword: str = Query("", description="Keyword; leer erlaubt"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    topic_id: Optional[int] = Query(None),
    topic_ids: Optional[str] = Query(None),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Sucht Abstracts (optional nach Topic gefiltert), paginiert."""
    client_ip = getattr(request.client, "host", "-")
    logger.info("GET /abstracts/search: kw='%s' page=%s size=%s topic_id=%s topic_ids=%s ip=%s",
                keyword, page, page_size, topic_id, topic_ids, client_ip)

    try:
        result = await search_abstracts_service(
            request, session, keyword, page, page_size, topic_id, topic_ids
        )
        logger.debug("/abstracts/search: result_keys=%s", list(result.keys()))
        return result
    except Exception:
        logger.exception("/abstracts/search: unerwarteter Fehler")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="search_failed")


@router.get("/{abstract_id}")
async def get_abstract_detail(
    abstract_id: int, session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Detailansicht eines Abstracts inkl. Autoren & Topics."""
    logger.info("GET /abstracts/%s", abstract_id)

    obj = session.get(Abstract, abstract_id)
    if not obj:
        logger.warning("GET /abstracts/%s: abstract_not_found", abstract_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="abstract_not_found")

    response = {
        "id": obj.id,
        "title": obj.title,
        "content_raw": obj.content_raw,
        "content": obj.content,
        "submission_date": obj.submission_date.isoformat() if obj.submission_date else None,
        "publication_date": obj.publication_date.isoformat() if obj.publication_date else None,
        "language_ref": obj.language_ref,
        "word_count": obj.word_count,
        "keywords": obj.keywords,
        "session_id": obj.session_id,
        "session_title": obj.session_title,
        "authors": [{"id": a.id, "name": a.name} for a in obj.authors],
        "topics": [{"id": t.id, "title": t.title} for t in obj.topics],
    }
    logger.debug("GET /abstracts/%s: authors=%s topics=%s", abstract_id, len(obj.authors), len(obj.topics))
    return response


@router.post("/import")
async def import_abstracts(
    request: Request, file: UploadFile, session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Importiert Abstracts aus einer bereitgestellten JSON-Datei (Service)."""
    logger.info("POST /abstracts/import: filename=%s content_type=%s", file.filename, file.content_type)
    try:
        result = await import_json_service(request, session, file)
        logger.debug("/abstracts/import: import_result_keys=%s", list(result.keys()))
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("/abstracts/import: Fehler beim Import-Service")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="import_failed")


# ────────────────────────────────────────────────────────────────────────────────
# PATCH ABSTRACT
# ────────────────────────────────────────────────────────────────────────────────
@router.patch("/{abstract_id}")
async def patch_abstract(
    abstract_id: int,
    request: Request,
    payload: Dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Aktualisiert Felder des Abstracts und pflegt ggf. Topic-Links.

    Wenn sich inhaltstragende Felder (title/content_raw/content) ändern, wird
    das Embedding neu berechnet und der FAISS-Index aktualisiert.
    """
    logger.info("PATCH /abstracts/%s: payload_keys=%s", abstract_id, list(payload.keys()))

    obj = session.get(Abstract, abstract_id)
    if not obj:
        logger.warning("PATCH /abstracts/%s: abstract_not_found", abstract_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="abstract_not_found")

    # track, ob wir Embedding neu rechnen müssen
    content_fields = ("title", "content_raw", "content")
    must_reembed = any(k in payload for k in content_fields)

    # einfache Feld-Updates (nur, wenn im Payload vorhanden)
    for k in [
        "title",
        "content_raw",
        "content",
        "submission_date",
        "publication_date",
        "language_ref",
        "word_count",
        "keywords",
        "session_id",
        "session_title",
    ]:
        if k in payload:
            v = payload[k]
            # Datum-Parsing (optional)
            if (
                k in ("submission_date", "publication_date")
                and isinstance(v, str)
                and v
            ):
                try:
                    v = datetime.fromisoformat(v)
                except Exception:
                    logger.warning("PATCH /abstracts/%s: invalid_datetime:%s", abstract_id, k)
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid_datetime:{k}")
            setattr(obj, k, v)

    # Topics (optional): payload.topics = [{"id": 28, "title": "..."}, ...]
    if "topics" in payload and isinstance(payload["topics"], list):
        logger.debug("PATCH /abstracts/%s: topics payload length=%s", abstract_id, len(payload["topics"]))
        # existierende Links lesen
        current_links = session.exec(
            select(AbstractTopicLink).where(AbstractTopicLink.abstract_id == abstract_id)
        ).all()
        current_topic_ids = {ln.topic_id for ln in current_links}

        # gewünschte Topic-IDs vorbereiten (anlegen falls neu)
        desired_topic_ids: set[int] = set()
        for t in payload["topics"]:
            if not isinstance(t, dict):
                continue
            t_id = t.get("id")
            t_title = t.get("title")
            if t_id is None or t_title is None:
                continue
            t_id = int(t_id)
            topic = session.get(Topic, t_id)
            if not topic:
                topic = Topic(id=t_id, title=str(t_title))
                session.add(topic)
            desired_topic_ids.add(t_id)

        # Links hinzufügen
        to_add = desired_topic_ids - current_topic_ids
        for t_id in to_add:
            session.add(AbstractTopicLink(abstract_id=abstract_id, topic_id=t_id))

        # Links entfernen
        to_remove = current_topic_ids - desired_topic_ids
        if to_remove:
            session.query(AbstractTopicLink).filter(
                AbstractTopicLink.abstract_id == abstract_id,
                AbstractTopicLink.topic_id.in_(to_remove),
            ).delete(synchronize_session=False)

    # Commit DB
    try:
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("PATCH /abstracts/%s: commit für Feld-Updates fehlgeschlagen", abstract_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="update_failed")

    # Re-Embedding & Reindexing wenn nötig
    if must_reembed:
        logger.info("PATCH /abstracts/%s: re-embedding angefordert", abstract_id)
        model = getattr(request.app.state, "model", None)
        if model:
            text_for_embed = f"{obj.title or ''}. {obj.content_raw or ''}".strip()
            try:
                vec = encode_texts(model, [text_for_embed])[0]  # shape (dim,)
                obj.embedding = vec.tolist()
                session.commit()
                logger.debug("PATCH /abstracts/%s: embedding aktualisiert", abstract_id)
            except Exception:
                session.rollback()
                logger.exception("PATCH /abstracts/%s: Fehler beim Re-Embedding/Commit", abstract_id)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="reembed_failed")

            # Index upsert (defensiv, falls Index-Komponente fehlt)
            try:
                indices = getattr(request.app.state, "indices", None)
                if indices and getattr(indices, "abs", None):
                    indices.abs.add_or_update([obj.id], [vec])
                    logger.debug("PATCH /abstracts/%s: abs-index add_or_update OK", abstract_id)
                else:
                    logger.warning("PATCH /abstracts/%s: abs-index nicht verfügbar", abstract_id)
            except Exception:
                logger.exception("PATCH /abstracts/%s: Fehler beim Index-Upsert", abstract_id)
        else:
            logger.warning("PATCH /abstracts/%s: kein Modell im App-State — Re-Embedding übersprungen", abstract_id)

    # Rückgabe (knapp; UI nutzt in der Regel die Detailroute)
    return {"status": "ok", "id": obj.id, "reembedded": bool(must_reembed)}


# ────────────────────────────────────────────────────────────────────────────────
# DELETE ABSTRACT
# ────────────────────────────────────────────────────────────────────────────────
@router.delete("/{abstract_id}")
async def delete_abstract(
    abstract_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Löscht ein Abstract inkl. Linktabellen und bereinigt FAISS.

    Vorab werden für alle verknüpften Autor:innen die Embeddings neu berechnet
    (ohne das zu löschende Abstract) und der Author-Index aktualisiert.
    """
    logger.info("DELETE /abstracts/%s", abstract_id)

    obj = session.get(Abstract, abstract_id)
    if not obj:
        logger.warning("DELETE /abstracts/%s: abstract_not_found", abstract_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="abstract_not_found")

    # 1) Betroffene Autor:innen merken (vor dem Löschen)
    affected_author_ids = [a.id for a in obj.authors]

    # 2) Autor-Embeddings ohne dieses Abstract neu berechnen
    #    - Wenn ein*e Autor*in danach keine Abstracts mehr hat: Embedding = None und aus Index entfernen
    import numpy as np

    upsert_ids: list[int] = []
    upsert_vecs: list[np.ndarray] = []
    remove_author_ids: list[int] = []

    if affected_author_ids:
        logger.debug("DELETE /abstracts/%s: affected_authors=%s", abstract_id, affected_author_ids)
        for aid in affected_author_ids:
            # Alle verbleibenden Abstracts *ohne* das zu löschende
            remaining_abs = (
                session.query(Abstract)
                .join(AbstractAuthorLink, AbstractAuthorLink.abstract_id == Abstract.id)
                .filter(
                    AbstractAuthorLink.author_id == aid,
                    Abstract.id != abstract_id,
                    Abstract.embedding != None,  # noqa: E711
                )
                .all()
            )
            if not remaining_abs:
                # Kein Embedding mehr ableitbar -> in DB auf None, und aus Index entfernen
                auth_obj = session.get(Author, aid)
                if auth_obj:
                    auth_obj.embedding = None
                remove_author_ids.append(aid)
                continue

            # Mean-Embedding bilden
            vecs = np.asarray([r.embedding for r in remaining_abs], dtype=np.float32)
            mean_vec = vecs.mean(axis=0)

            # In DB speichern
            auth_obj = session.get(Author, aid)
            if auth_obj:
                auth_obj.embedding = mean_vec.tolist()

            # Für Index-Upsert sammeln
            upsert_ids.append(aid)
            upsert_vecs.append(mean_vec.astype(np.float32))

        # Änderungen an Autoren persistieren (vor Löschen des Abstracts)
        try:
            session.commit()
            logger.debug("DELETE /abstracts/%s: Autoren-Embeddings aktualisiert (upsert=%s, remove=%s)",
                         abstract_id, len(upsert_ids), len(remove_author_ids))
        except Exception:
            session.rollback()
            logger.exception("DELETE /abstracts/%s: commit Autoren fehlgeschlagen", abstract_id)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="author_update_failed")

        # Author-Index aktualisieren (Upsert / Remove)
        try:
            indices = getattr(request.app.state, "indices", None)
            if indices and getattr(indices, "auth", None):
                if upsert_ids:
                    indices.auth.add_or_update(upsert_ids, upsert_vecs)
                if remove_author_ids:
                    indices.auth.remove(remove_author_ids)
                logger.debug("DELETE /abstracts/%s: author-index aktualisiert", abstract_id)
            else:
                logger.warning("DELETE /abstracts/%s: author-index nicht verfügbar", abstract_id)
        except Exception:
            # Fehler im Index nicht fatal für DB-Konsistenz, aber loggen
            logger.exception("DELETE /abstracts/%s: Fehler beim Author-Index-Update", abstract_id)

    # 3) Links löschen und Abstract entfernen
    try:
        session.query(AbstractAuthorLink).filter(
            AbstractAuthorLink.abstract_id == abstract_id
        ).delete(synchronize_session=False)

        session.query(AbstractTopicLink).filter(
            AbstractTopicLink.abstract_id == abstract_id
        ).delete(synchronize_session=False)

        session.delete(obj)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("DELETE /abstracts/%s: Fehler beim Löschen/Commit", abstract_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="delete_failed")

    # 4) Abstract-Index bereinigen
    try:
        indices = getattr(request.app.state, "indices", None)
        if indices and getattr(indices, "abs", None):
            indices.abs.remove([abstract_id])
            logger.debug("DELETE /abstracts/%s: abs-index remove OK", abstract_id)
        else:
            logger.warning("DELETE /abstracts/%s: abs-index nicht verfügbar", abstract_id)
    except Exception:
        logger.exception("DELETE /abstracts/%s: Fehler beim Entfernen aus abs-index", abstract_id)

    return {
        "status": "ok",
        "deleted": abstract_id,
        "authors_reembedded": len(upsert_ids),
        "authors_removed_from_index": len(remove_author_ids),
    }
