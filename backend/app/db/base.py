"""\
app/db/base.py — zentrale DB-Engine & Session-Utilities

Ziele:
- Engine erstellen (mit Connection-Pool-Settings)
- Session-Generator für FastAPI-Dependencies
- Convenience-Funktionen fürs manuelle Öffnen/Benutzen einer Session
- Logging der Engine-Parameter (sensibel maskiert)
"""

from __future__ import annotations

# ── Standardbibliothek
import logging
from contextlib import contextmanager
from typing import Generator, Iterator
from urllib.parse import urlparse

# ── Drittanbieter
from sqlmodel import Session, create_engine

# ── Lokale Module
from app.config import settings


# ────────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


def _mask_database_url(url: str) -> str:
    """Maskiert sensible Teile der DB-URL für Logs (User/Pass)."""
    try:
        p = urlparse(url)
        host = p.hostname or "?"
        port = f":{p.port}" if p.port else ""
        path = p.path or ""
        return f"{p.scheme}://{host}{port}{path}"
    except Exception:
        # Fallback: nur den Teil nach '@' zeigen (falls vorhanden)
        return url.split("@")[-1]


# ────────────────────────────────────────────────────────────────────────────────
# Engine-Konfiguration
# ────────────────────────────────────────────────────────────────────────────────
# Connection-Pooling ist wichtig, um in Produktions-Setups (z. B. Gunicorn/Uvicorn
# mit mehreren Workern) stabil und performant mit Postgres zu arbeiten.
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,       # Anzahl persistenter Verbindungen im Pool
    max_overflow=20,    # zusätzliche Verbindungen bei Last
    pool_timeout=30,    # Sekunden bis Timeout beim Ausleihen einer Connection
    pool_pre_ping=True, # prüft Connections auf Gültigkeit (verhindert Stale-Errors)
    future=True,        # aktiviert SQLAlchemy 2.0-kompatibles Verhalten
)

# Einmalig beim Modulimport loggen
try:
    logger.info(
        "DB engine initialized (url=%s, pool_size=%d, max_overflow=%d, timeout=%ds, pre_ping=%s)",
        _mask_database_url(settings.DATABASE_URL),
        10,
        20,
        30,
        True,
    )
except Exception:
    logger.debug("failed to log DB engine init info", exc_info=True)


# ────────────────────────────────────────────────────────────────────────────────
# Session-Utilities
# ────────────────────────────────────────────────────────────────────────────────

def get_session() -> Generator[Session, None, None]:
    """FastAPI-Dependency: liefert eine DB-Session im Kontext-Manager.

    Beispiel:
        def endpoint(db: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session


def open_session() -> Session:
    """Öffnet eine neue Session manuell.

    Nutzer:in ist selbst verantwortlich für Schließen/Commit/Rollback.
    Geeignet für Skripte, Migrations-Tasks oder Admin-Operationen.
    """
    return Session(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context-Manager mit Auto-Commit/Rollback für Skripte.

    Beispiel:
        with session_scope() as db:
            db.add(obj)
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
