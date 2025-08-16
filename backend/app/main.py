"""\
app/main.py — Einstiegspunkt der FastAPI-Anwendung

Ziele dieses Moduls:
- Logging, Thread-/BLAS-Limits und Modell/Index-Setup deterministisch beim Start (lifespan)
- Datenbank initialisieren
- FAISS-Indizes für Abstracts und Autor:innen laden/erzeugen
- Router registrieren (mit korrekter Reihenfolge statisch > dynamisch)
- CORS sauber konfigurieren

"""

from __future__ import annotations

# ── Standardbibliothek
import logging
import os
import sys
import threading
from contextlib import asynccontextmanager
from typing import AsyncIterator

# ── Drittanbieter
import faiss  # Typ: ignore
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

# ── Lokale Module
from app.api import routes_abstracts, routes_admin, routes_authors, routes_topics
from app.config import settings
from app.db.base import engine
from app.db.init import init_db
from app.embeddings.encoder import load_model
from app.index.service import IndexService, MultiIndex


# ────────────────────────────────────────────────────────────────────────────────
# Lifespan-Manager: zentraler Ort für Startup/Shutdown-Logik
# ────────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Richtet die Anwendung beim Start ein und persistiert Ressourcen beim Shutdown.

    Reihenfolge & Gründe:
    1) Logging: Einheitliches Format & Level bereits beim Start.
    2) Thread-/BLAS-Limits: Stabilität/Determinismus in Containern (wichtig für FAISS/NumPy/MKL).
    3) DB-Init: Tabellen anlegen, ggf. Migrationslogik anstoßen (siehe ``init_db``).
    4) Embedding-Modell laden: Modell & Metadaten in ``app.state`` bereitstellen.
    5) Indizes vorbereiten: Services für Abstracts & Autor:innen (L2-Metrik) anlegen
       und entweder bestehende Dateien laden oder neu bauen.
    6) Backwards-Kompatibilität: Historische Aliasse auf ``app.state`` beibehalten.
    7) Shutdown: Indizes persistieren (``save``).
    """

    # 1) Logging möglichst früh konfigurieren
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    # 2) Thread-/BLAS-Limits für deterministische Inferenz und stabile Latenzen
    #    (Hinweis: Idealerweise früh im Prozess setzen, hier reicht es für FAISS.)
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
    faiss.omp_set_num_threads(1)

    # 3) Datenbank initialisieren (Tabellen etc.)
    init_db()

    # 4) Embedding-Modell laden und auf dem Application-State ablegen
    model, actual_device = load_model(settings.EMBED_MODEL, settings.EMBED_DEVICE)
    app.state.model = model
    app.state.model_name = settings.EMBED_MODEL
    app.state.model_device = actual_device

    # Optionale Score-Anzeige/-Modus aus Konfiguration
    app.state.show_scores = settings.SHOW_SCORES
    app.state.score_mode = settings.SCORE_MODE

    # 5) Index-Services einrichten (Abstracts & Autor:innen, L2-Metrik)
    #    Pfade sind kompatibel zum existierenden FAISS-Score-Pfad
    abstracts_index_path = os.path.join(settings.INDEX_DIR, "abstracts.index")
    authors_index_path = os.path.join(settings.INDEX_DIR, "authors.index")

    abs_service = IndexService(
        dim=settings.VECTOR_DIM,
        metric="l2",
        index_path=abstracts_index_path,
    )
    auth_service = IndexService(
        dim=settings.VECTOR_DIM,
        metric="l2",
        index_path=authors_index_path,
    )

    # Gemeinsame MultiIndex-Hülle, damit Aufrufe symmetrisch möglich sind
    app.state.indices = MultiIndex(abs_service, auth_service)

    # Laden oder (falls nicht vorhanden) Aufbau der Indizes
    with Session(engine) as session:
        app.state.indices.load_or_build(session)

    # 6) Backwards-Compat: historische Aliasse weiter bereitstellen
    app.state.abstract_index = app.state.indices.abs.index
    app.state.author_index = app.state.indices.auth.index

    # Reentrant-Lock für FAISS-Operationen in parallelen Requests
    app.state.faiss_lock = threading.RLock()

    # Kontrollfluss an die App übergeben (Server läuft)
    yield

    # 7) Shutdown: Indizes persistieren (z. B. nach Inkrement-Updates)
    app.state.indices.save()


# ────────────────────────────────────────────────────────────────────────────────
# FastAPI-App erstellen und konfigurieren
# ────────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Embedding API", version="0.1.0", lifespan=lifespan)

# CORS-Konfiguration: Frontend-Entwicklung & produktiver Origin
# - Falls FRONTEND_ORIGIN nicht gesetzt ist, wird er herausgefiltert
allowed_origins = [settings.FRONTEND_ORIGIN, "http://localhost:5173"]
allowed_origins = [o for o in allowed_origins if o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router registrieren
# Wichtig: statische Routen (z. B. /search) vor dynamischen Mustern einbinden,
# damit Matching/Overlaps eindeutig bleibt.
app.include_router(routes_authors.router, prefix="/authors")
app.include_router(routes_abstracts.router, prefix="/abstracts")
app.include_router(routes_topics.router)
app.include_router(routes_admin.router)  # /admin/*


# ────────────────────────────────────────────────────────────────────────────────
# Optional: Health-Endpoint (leichtgewichtig, keine Abhängigkeit auf FAISS/DB)
# ────────────────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])  # pragma: no cover
async def health() -> dict[str, str]:
    """Einfache Lebenszeichenprüfung für Load-Balancer/Probes."""
    return {"status": "ok", "model": app.state.model_name}
