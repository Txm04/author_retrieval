"""\
app/models/domain.py — ORM-Domain-Modelle mit SQLModel

Ziele:
- Zentrale Tabellen (Abstract, Author, Topic) + Link-Tabellen für n:m (Abstract↔Author, Abstract↔Topic)
- Einfache, robuste Typisierung mit SQLModel (SQLAlchemy 2.x kompatibel)
- Embeddings als PostgreSQL ARRAY(Float)
- Wichtig: KEIN `from __future__ import annotations` in dieser Datei, damit `typing.List[...]`
  NICHT zu String-Annotationen wird (vermeidet den Mapper-Fehler mit relationship/"List['…']").
"""

# ── Standardbibliothek
from typing import Optional, List
from datetime import datetime

# ── Drittanbieter (SQLModel / SQLAlchemy)
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Float
from sqlalchemy import DateTime as SA_DateTime
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY


# ────────────────────────────────────────────────────────────────────────────────
# Link-Tabellen (n:m-Beziehungen)
# ────────────────────────────────────────────────────────────────────────────────
class AbstractAuthorLink(SQLModel, table=True):
    """n:m-Verknüpfung zwischen Abstracts und Authors."""
    abstract_id: int = Field(foreign_key="abstract.id", primary_key=True)
    author_id: int = Field(foreign_key="author.id", primary_key=True)


class AbstractTopicLink(SQLModel, table=True):
    """n:m-Verknüpfung zwischen Abstracts und Topics."""
    abstract_id: int = Field(foreign_key="abstract.id", primary_key=True)
    topic_id: int = Field(foreign_key="topic.id", primary_key=True)


# ────────────────────────────────────────────────────────────────────────────────
# Haupt-Tabellen
# ────────────────────────────────────────────────────────────────────────────────
class Topic(SQLModel, table=True):
    """Thema/Cluster, dem mehrere Abstracts zugeordnet sein können."""
    # Hinweis: Feste int-IDs (kein Autoincrement nötig). Falls Autoincrement gewünscht:
    # id: Optional[int] = Field(default=None, primary_key=True)
    id: int = Field(primary_key=True)
    title: str

    # Beziehung: viele Abstracts pro Topic (n:m via Linktabelle)
    # WICHTIG: `List["Abstract"]` (aus typing) funktioniert hier bewusst ohne __future__.
    abstracts: List["Abstract"] = Relationship(
        back_populates="topics",
        link_model=AbstractTopicLink,
    )


class Abstract(SQLModel, table=True):
    """Wissenschaftliches Abstract inkl. Metadaten und Embedding."""
    id: int = Field(primary_key=True)

    # Inhalt
    title: str
    content_raw: str
    content: Optional[str] = None

    # Zeitliche Angaben (mit Zeitzone in der DB)
    submission_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(SA_DateTime(timezone=True)),
    )
    publication_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(SA_DateTime(timezone=True)),
    )

    # Metadaten
    language_ref: Optional[int] = None
    word_count: Optional[int] = None
    keywords: Optional[str] = None
    session_id: Optional[int] = None
    session_title: Optional[str] = None

    # Embedding-Vektor (PostgreSQL ARRAY(Float)); None falls nicht berechnet
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(PG_ARRAY(Float), nullable=True),
        description="Embedding-Vektor als float32-Array (DB: Postgres ARRAY(Float))",
    )

    # Beziehungen (n:m via Linktabellen)
    authors: List["Author"] = Relationship(
        back_populates="abstracts",
        link_model=AbstractAuthorLink,
    )
    topics: List[Topic] = Relationship(
        back_populates="abstracts",
        link_model=AbstractTopicLink,
    )


class Author(SQLModel, table=True):
    """Autor:in; Embedding typischerweise Mittelwert über zugehörige Abstract-Embeddings."""
    id: int = Field(primary_key=True)
    name: str

    # Optionales Embedding (Mean über Abstracts); None, wenn nicht ableitbar
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(PG_ARRAY(Float), nullable=True),
    )

    # Beziehung: viele Abstracts pro Autor:in (n:m via Linktabelle)
    abstracts: List[Abstract] = Relationship(
        back_populates="authors",
        link_model=AbstractAuthorLink,
    )
