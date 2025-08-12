# app/db/base.py
from sqlmodel import create_engine, Session
from typing import Generator
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_pre_ping=True,
    future=True,
)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def open_session() -> Session:
    return Session(engine)
