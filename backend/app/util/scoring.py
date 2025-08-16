"""
app/util/scoring.py — Hilfsfunktionen für Similarity-Scoring

Ziele:
- Einheitliche Berechnung von Similarity-Scores für Vektoren
- Unterstützt Cosine Similarity und Transformation von FAISS-L2-Distanzen
"""

import logging
import numpy as np

# ────────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """
    Berechnet die Cosine Similarity zweier Vektoren.

    Rückgabe:
        Wert im Bereich [-1, 1], wobei
        - 1.0 = identische Richtung
        - 0.0 = orthogonal
        - -1.0 = entgegengesetzt

    Falls einer der Vektoren Norm 0 hat, wird 0.0 zurückgegeben.
    """
    da, db = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if da == 0.0 or db == 0.0:
        logger.debug("Cosine similarity: zero vector detected (da=%.3f, db=%.3f)", da, db)
        return 0.0
    return float(np.dot(a, b) / (da * db))


def faiss_score_from_l2(d: float) -> float:
    """
    Transformiert eine FAISS-L2-Distanz (>=0) in einen Score ∈ (0,1].

    Formel: score = 1 / (1 + d)
      - d=0  -> 1.0 (identisch)
      - d→∞ -> 0.0 (sehr unähnlich)

    Hinweis: Das ist eine heuristische Transformation,
    nicht direkt vergleichbar mit Cosine Similarity.
    """
    if d < 0:
        logger.warning("faiss_score_from_l2: negative distance %f", d)
    return float(1.0 / (1.0 + float(d)))
