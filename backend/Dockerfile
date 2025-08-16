# ---- Base (CPU) ----
FROM python:3.13-slim AS base
LABEL authors="tomeichhorn"

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git ca-certificates \
    libpq5 libpq-dev gosu \
    && rm -rf /var/lib/apt/lists/*

# App-User anlegen (UID 1000 -> passt gut zu host)
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Requirements zuerst (Layer-Caching)
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r /app/requirements.txt

# App-Code
COPY backend/app /app/app
COPY backend/gunicorn_conf.py /app/gunicorn_conf.py

# Standard-Indexpfad IM Container (überschreibbar per ENV/Compose)
ENV INDEX_DIR=/app/.indices \
    FRONTEND_ORIGIN=http://localhost:3000 \
    EMBED_MODEL=all-MiniLM-L6-v2 \
    EMBED_DEVICE=cpu

# Index-Verz. anlegen & Rechte setzen (funktioniert ohne Volume)
RUN mkdir -p "${INDEX_DIR}" && chown -R appuser:appuser "${INDEX_DIR}"

# Entrypoint, der zur Laufzeit Rechte für gemountetes Volume setzt
COPY backend/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

# ENTRYPOINT läuft als root, droppt dann via gosu auf appuser
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn_conf.py", "app.main:app"]
