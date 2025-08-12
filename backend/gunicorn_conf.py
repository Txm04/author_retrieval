import multiprocessing
bind = "0.0.0.0:8000"
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
graceful_timeout = 30
keepalive = 10

# keep FAISS / BLAS from over-parallelizing
raw_env = [
    "OMP_NUM_THREADS=1",
    "MKL_NUM_THREADS=1",
    "VECLIB_MAXIMUM_THREADS=1",
]
