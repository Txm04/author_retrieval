"""\
app/services/import_json_service.py — JSON-Import für Abstracts/Autoren/Topics

Ziele:
- JSON-Datei einlesen und in die Datenbank upserten (Abstracts, Authors, Topics, Linktabellen)
- Embeddings für **neue** Abstracts erzeugen und persistieren
- Indizes inkrementell aktualisieren (Abstracts + Autor:innen)

Eigenschaften:
- Deduplizierung innerhalb der Import-Datei (pro (abstract_id, topic_id))
- Deduplizierung von Linktabellen in DB (Author↔Abstract, Abstract↔Topic)
- Robuste Logs mit Operations-ID (op_id)
- Defensive Datumskonvertierung (ISO-8601 → datetime) mit 400-Failure als Option
"""

from __future__ import annotations

# ── Standardbibliothek
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

# ── Drittanbieter
import numpy as np
from fastapi import Request, UploadFile
from sqlmodel import Session

# ── Lokale Module
from app.embeddings.encoder import encode_texts
from app.index.index_hooks import update_indices_after_import
from app.models.domain import (
    Abstract,
    AbstractAuthorLink,
    AbstractTopicLink,
    Author,
    Topic,
)


# ────────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ────────────────────────────────────────────────────────────────────────────────

def _safe_str(x: Optional[str]) -> str:
    """Gibt immer einen String zurück (leer statt None)."""
    return x or ""


def _parse_dt(v: Any) -> Optional[datetime]:
    """Parst ISO-8601-Strings zu datetime; lässt None/unveränderte Werte durch."""
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except Exception:
            # Soft-Failure: Wir geben None zurück und loggen Warnung, damit der Import nicht scheitert.
            logger.warning("invalid datetime string: %r", v)
            return None
    return None


# ────────────────────────────────────────────────────────────────────────────────
# Service
# ────────────────────────────────────────────────────────────────────────────────
async def import_json_service(
    request: Request,
    session: Session,
    file: UploadFile,
) -> Dict[str, Any]:
    """Importiert Abstracts/Autoren/Topics aus einer JSON-Datei.

    Ablauf:
    1) Datei lesen und grob validieren (Liste von Items)
    2) Upsert: neue Abstracts/Authors/Topics anlegen, Linktabellen deduplizieren
    3) Commit (Struktur), danach Embeddings für **neue** Abstracts erzeugen & committen
    4) Inkrementelle Index-Updates (Abstracts & Autor:innen)

    Rückgabe:
        { status, count, authors_updated, op_id, duration_ms }
    """
    op_id = uuid.uuid4().hex[:8]
    t0 = time.perf_counter()

    raw = await file.read()
    logger.info(
        "[%s] import start: filename=%s size=%dB",
        op_id,
        getattr(file, "filename", "<stream>"),
        len(raw),
    )

    # --- Parse & Grundvalidierung ------------------------------------------------
    try:
        data = json.loads(raw)
        assert isinstance(data, list)
    except Exception:
        logger.exception("[%s] invalid_json: parse/structure failed", op_id)
        return {"error": "invalid_json"}

    logger.debug("[%s] parsed items=%d", op_id, len(data))

    texts: List[str] = []
    new_abstracts: List[Abstract] = []
    abstract_author_links: List[AbstractAuthorLink] = []

    seen_in_file: set[tuple[int, Optional[int]]] = set()  # (abstract_id, topic_id)
    links_seen: set[tuple[int, int]] = set()  # (abstract_id, author_id)
    affected_author_ids: set[int] = set()

    skipped_dupe_pairs = 0
    created_topics = 0
    created_authors = 0

    # --- Upsert-Loop -------------------------------------------------------------
    for idx, item in enumerate(data):
        try:
            abstract_id = int(item["id"])  # Pflichtfeld
        except Exception:
            logger.warning("[%s] skip item@%d: missing/invalid id", op_id, idx)
            continue

        topic_id = item.get("topic_id")
        key_in_file = (abstract_id, topic_id)
        if key_in_file in seen_in_file:
            skipped_dupe_pairs += 1
            logger.debug(
                "[%s] skip duplicate (abstract_id=%s, topic_id=%s)",
                op_id,
                abstract_id,
                topic_id,
            )
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
                submission_date=_parse_dt(item.get("submission_date")),
                publication_date=_parse_dt(item.get("publication_date")),
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
        for auth_data in (item.get("authors", []) or []):
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
                created_authors += 1

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
                created_topics += 1

            link_exists = (
                session.query(AbstractTopicLink)
                .filter_by(abstract_id=abs_obj.id, topic_id=topic.id)
                .first()
            )
            if not link_exists:
                session.add(
                    AbstractTopicLink(abstract_id=abs_obj.id, topic_id=topic.id)
                )

    if abstract_author_links:
        session.add_all(abstract_author_links)

    # ---- Commit DB-Struktur, BEVOR Embeddings erzeugt werden -------------------
    try:
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("[%s] db commit failed (phase=links)", op_id)
        raise

    # ---- Embeddings für neue Abstracts persistieren ----------------------------
    added_abstracts = 0
    changed_abs_ids: List[int] = []
    if new_abstracts:
        model = request.app.state.model
        try:
            vecs = np.asarray(encode_texts(model, texts), dtype=np.float32)
        except Exception:
            logger.exception("[%s] embedding encode failed (count=%d)", op_id, len(texts))
            raise

        for abs_obj, vec in zip(new_abstracts, vecs):
            abs_obj.embedding = vec.tolist()

        try:
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("[%s] db commit failed (phase=embeddings)", op_id)
            raise

        added_abstracts = len(new_abstracts)
        changed_abs_ids = [a.id for a in new_abstracts]

        if changed_abs_ids:
            rows = (
                session.query(AbstractAuthorLink.author_id)
                .filter(AbstractAuthorLink.abstract_id.in_(changed_abs_ids))
                .all()
            )
            for (aid,) in rows:
                affected_author_ids.add(int(aid))

    # ---- Index-Update für Abstracts & Autor:innen (inkrementell) ---------------
    try:
        update_indices_after_import(
            request.app,
            session,
            changed_abs_ids=changed_abs_ids,
            changed_author_ids=affected_author_ids,
        )
    except Exception:
        logger.exception(
            "[%s] index update failed (abs=%d, authors=%d)",
            op_id,
            len(changed_abs_ids),
            len(affected_author_ids),
        )
        raise

    dt = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "[%s] import done: items=%d new_abs=%d new_authors=%d new_topics=%d dupe_pairs_skipped=%d affected_authors=%d duration_ms=%.1f",
        op_id,
        len(data),
        added_abstracts,
        created_authors,
        created_topics,
        skipped_dupe_pairs,
        len(affected_author_ids),
        dt,
    )

    return {
        "status": "imported",
        "count": added_abstracts,
        "authors_updated": len(affected_author_ids),
        "op_id": op_id,
        "duration_ms": round(dt, 1),
    }
