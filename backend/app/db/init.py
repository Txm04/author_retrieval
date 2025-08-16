"""\
app/db/init.py — Datenbank-Initialisierung & Reset

Ziele:
- `init_db`: Erzeugt alle Tabellen basierend auf dem SQLModel-Metadatenmodell.
- `reset_db`: Droppt alle Tabellen und legt sie neu an (nur für Tests/Entwicklung geeignet!).
"""

from __future__ import annotations
import logging
from sqlmodel import SQLModel
from .base import engine

# ────────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

def init_db(engine=engine) -> None:
    """Erstellt alle Tabellen, falls sie noch nicht existieren.

    Hinweis: Für Produktionssysteme sollte man Migrationstools wie Alembic nutzen.
    """
    logger.info("initializing database schema…")
    SQLModel.metadata.create_all(engine)
    logger.info("database schema initialized.")


def reset_db(engine=engine) -> None:
    """Droppt alle Tabellen und legt sie neu an.

    Vorsicht: Löscht sämtliche Daten unwiderruflich.
    Nur in Entwicklungs- oder Testumgebungen verwenden, nicht in Produktion.
    """
    logger.warning("resetting database schema — ALL DATA WILL BE LOST!")
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    logger.info("database schema reset complete.")
