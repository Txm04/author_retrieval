# app/index/faiss_index.py
import faiss, numpy as np
from app.db.base import open_session
from app.models.domain import Abstract, Author
from app.config import settings

VECTOR_DIM = settings.VECTOR_DIM

def _stack_embeddings(rows):
    vecs = np.array([r.embedding for r in rows], dtype=np.float32)
    if vecs.ndim != 2 or vecs.shape[1] != VECTOR_DIM:
        raise ValueError(f"Embedding matrix has shape {vecs.shape}, expected (N, {VECTOR_DIM})")
    return np.ascontiguousarray(vecs, dtype=np.float32)

def build_indices(model=None):
    sess = open_session()

    # Always create empty indices
    abstract_idx = faiss.IndexIDMap(faiss.IndexFlatL2(VECTOR_DIM))
    author_idx   = faiss.IndexIDMap(faiss.IndexFlatL2(VECTOR_DIM))

    # Fill abstracts
    abs_rows = sess.query(Abstract).filter(Abstract.embedding != None).all()
    if abs_rows:
        vecs = _stack_embeddings(abs_rows)
        ids  = np.ascontiguousarray(np.array([a.id for a in abs_rows], dtype=np.int64))
        abstract_idx.add_with_ids(vecs, ids)

    # Fill authors
    auth_rows = sess.query(Author).filter(Author.embedding != None).all()
    if auth_rows:
        vecs = _stack_embeddings(auth_rows)
        ids  = np.ascontiguousarray(np.array([a.id for a in auth_rows], dtype=np.int64))
        author_idx.add_with_ids(vecs, ids)

    return abstract_idx, author_idx