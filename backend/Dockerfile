# ---- Base (CPU) ----
FROM python:3.13-slim AS base
LABEL authors="tomeichhorn"

# Avoid interactive tz/data prompts
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for psycopg2 + FAISS + torch
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git ca-certificates \
    libpq5 libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m appuser
WORKDIR /app

# Copy requirements first (layer cache)
COPY backend/requirements.txt /app/requirements.txt

# Install Python deps
# - If you use psycopg2-binary, you can drop libpq-dev above.
RUN pip install --upgrade pip \
 && pip install -r /app/requirements.txt

# Copy source
COPY backend/app /app/app
COPY backend/gunicorn_conf.py /app/gunicorn_conf.py

# Security: drop privileges
USER appuser

# For healthcheck and gunicorn/uvicorn
EXPOSE 8000

# Default envs (overridden by docker-compose)
ENV FRONTEND_ORIGIN=http://localhost:3000 \
    EMBED_MODEL=all-MiniLM-L6-v2 \
    EMBED_DEVICE=cpu

# Start with gunicorn (multi-worker) for prod
# FastAPI app lives in app/main.py -> app:app
CMD ["gunicorn", "-c", "gunicorn_conf.py", "app.main:app"]
