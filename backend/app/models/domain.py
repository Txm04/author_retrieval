# app/models/domain.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, Float
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy import DateTime as SA_DateTime

class AbstractAuthorLink(SQLModel, table=True):
    abstract_id: int = Field(foreign_key="abstract.id", primary_key=True)
    author_id: int = Field(foreign_key="author.id", primary_key=True)

class AbstractTopicLink(SQLModel, table=True):
    abstract_id: int = Field(foreign_key="abstract.id", primary_key=True)
    topic_id: int = Field(foreign_key="topic.id", primary_key=True)

class Topic(SQLModel, table=True):
    id: int = Field(primary_key=True)
    title: str
    abstracts: List["Abstract"] = Relationship(back_populates="topics", link_model=AbstractTopicLink)

class Abstract(SQLModel, table=True):
    id: int = Field(primary_key=True)
    title: str
    content_raw: str
    content: Optional[str] = None
    submission_date: Optional[datetime] = Field(default=None, sa_column=Column(SA_DateTime(timezone=True)))
    publication_date: Optional[datetime] = Field(default=None, sa_column=Column(SA_DateTime(timezone=True)))
    language_ref: Optional[int] = None
    word_count: Optional[int] = None
    keywords: Optional[str] = None
    session_id: Optional[int] = None
    session_title: Optional[str] = None
    embedding: Optional[List[float]] = Field(default=None, sa_column=Column(PG_ARRAY(Float), nullable=True))

    authors: List["Author"] = Relationship(back_populates="abstracts", link_model=AbstractAuthorLink)
    topics: List[Topic] = Relationship(back_populates="abstracts", link_model=AbstractTopicLink)

class Author(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    embedding: Optional[List[float]] = Field(default=None, sa_column=Column(PG_ARRAY(Float), nullable=True))

    abstracts: List[Abstract] = Relationship(back_populates="authors", link_model=AbstractAuthorLink)
