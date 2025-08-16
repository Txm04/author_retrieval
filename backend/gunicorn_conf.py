"""
gunicorn_conf.py — Gunicorn-Konfiguration für FastAPI/Uvicorn

Kommentarübersicht
------------------
- Bind-Adresse & Port: Auf allen Interfaces, Port 8000
- Worker-Setup: Ein Prozess, UvicornWorker als Async-Server
- Timeouts: großzügige Limits für lange Requests
- Keepalive: Verbindungsoffenhaltung für Performance
- raw_env: Umgebungsvariablen, um FAISS/BLAS-Threads zu begrenzen
"""

# Adresse & Port, auf denen Gunicorn lauscht
bind = "0.0.0.0:8000"

# Anzahl Worker-Prozesse — hier bewusst 1, weil FAISS/BLAS CPU-intensiv ist
workers = 1

# Worker-Klasse: UvicornWorker für asynchrone FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Request-Timeouts
# - timeout: Maximale Dauer (Sekunden) bis ein Request abgeschlossen sein muss
# - graceful_timeout: Zeit für sauberes Beenden (Shutdown)
# - keepalive: Zeit (Sekunden), wie lange eine Verbindung offen gehalten wird
#   für Folge-Requests

timeout = 600            # lange Anfragen (z. B. Re-Indexing) zulassen
graceful_timeout = 30    # max. 30 Sekunden für Graceful Shutdown
keepalive = 10           # HTTP Keep-Alive Dauer

# Umgebungsvariablen setzen, um parallele Threads bei BLAS/FAISS zu limitieren
# → Verhindert Über-Parallelisierung, die zu Instabilität/Latenzspitzen führt
raw_env = [
    "OMP_NUM_THREADS=1",     # OpenMP Threads limitieren
    "MKL_NUM_THREADS=1",     # Intel MKL Threads limitieren
    "VECLIB_MAXIMUM_THREADS=1",  # Apple Accelerate/vecLib Threads limitieren
]
