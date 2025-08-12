# app/util/scoring.py
import numpy as np
def cosine(a: np.ndarray, b: np.ndarray) -> float:
    da, db = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if da == 0.0 or db == 0.0: return 0.0
    return float(np.dot(a, b) / (da * db))

def faiss_score_from_l2(d: float) -> float:
    return float(1.0 / (1.0 + float(d)))
