# app/db/init.py
from sqlmodel import SQLModel
from .base import engine

def init_db():
    SQLModel.metadata.create_all(engine)

def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
