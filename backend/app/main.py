# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import threading, os, faiss
from app.db.init import init_db, reset_db
from app.embeddings.encoder import load_model
from app.index.faiss_index import build_indices
from app.api import routes_admin, routes_authors, routes_abstracts, routes_topics
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.environ["OMP_NUM_THREADS"]="1"; os.environ["MKL_NUM_THREADS"]="1"; os.environ["VECLIB_MAXIMUM_THREADS"]="1"
    faiss.omp_set_num_threads(1)

    init_db()
    model, actual = load_model(settings.EMBED_MODEL, settings.EMBED_DEVICE)
    app.state.model = model
    app.state.model_name = settings.EMBED_MODEL
    app.state.model_device = actual
    app.state.show_scores = settings.SHOW_SCORES
    app.state.score_mode = settings.SCORE_MODE

    abstract_idx, author_idx = build_indices(model)
    app.state.abstract_index = abstract_idx
    app.state.author_index = author_idx
    app.state.faiss_lock = threading.RLock()
    yield

app = FastAPI(title="Embedding API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Wichtig: statische Routen (search) VOR dynamischen
app.include_router(routes_authors.router, prefix="/authors")
app.include_router(routes_abstracts.router, prefix="/abstracts")
app.include_router(routes_topics.router)
app.include_router(routes_admin.router)  # /admin/*
