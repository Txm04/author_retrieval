"""\
app/embeddings/encoder.py — Laden & Anwenden von SentenceTransformer-Modellen

Ziele:
- Modell (SentenceTransformer) mit Device-Auswahl laden
- Texte in Float32-Vektoren enkodieren (kompatibel mit FAISS)
"""

from __future__ import annotations

# ── Standardbibliothek
from typing import Tuple
import logging

# ── Drittanbieter
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

# ── Lokale Module
from app.config import settings

# ────────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Modell-Ladefunktion
# ────────────────────────────────────────────────────────────────────────────────

def load_model(
    model_name: str = settings.EMBED_MODEL,
    device: str | None = settings.EMBED_DEVICE,
) -> Tuple[SentenceTransformer, str]:
    """Lädt ein SentenceTransformer-Modell auf das passende Device.

    - Wenn `device` nicht angegeben ist, wird automatisch ein geeignetes gewählt:
      1) CUDA (NVIDIA-GPU)
      2) MPS (Apple Silicon)
      3) CPU (Fallback)

    Args:
        model_name: Name/Checkpoint des SentenceTransformer-Modells
        device: Zielgerät ("cpu", "cuda", "mps" oder None für Auto)

    Returns:
        Tuple[model, actual_device]
    """
    if device is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

    logger.info("loading sentence-transformer: name=%s device=%s", model_name, device)
    model = SentenceTransformer(model_name, device=device)
    logger.debug(
        "model loaded: dim=%s modules=%s",
        getattr(model, "get_sentence_embedding_dimension", lambda: "?")(),
        list(model._modules.keys()) if hasattr(model, "_modules") else "?",
    )
    return model, device


# ────────────────────────────────────────────────────────────────────────────────
# Encoding-Funktion
# ────────────────────────────────────────────────────────────────────────────────

def encode_texts(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    """Kodiert eine Liste von Texten zu Float32-Vektoren.

    Args:
        model: Vorab geladenes SentenceTransformer-Modell
        texts: Liste von Strings, die eingebettet werden sollen

    Returns:
        NumPy-Array der Form (len(texts), dim) mit dtype float32.
        Float32 ist wichtig, da FAISS diese Präzision erwartet und
        Speicher/Performance optimiert.
    """
    if not texts:
        # Leere Eingabe → leeres Array mit korrekter Dim zurückgeben
        dim = (
            model.get_sentence_embedding_dimension()
            if hasattr(model, "get_sentence_embedding_dimension")
            else 0
        )
        logger.debug("encode_texts: empty input → shape=(0,%d)", dim)
        return np.zeros((0, int(dim)), dtype=np.float32)

    logger.debug("encode_texts: count=%d", len(texts))
    try:
        emb = model.encode(texts, convert_to_numpy=True)
    except Exception:
        logger.exception("encode_texts failed (count=%d)", len(texts))
        raise
    out = emb.astype(np.float32, copy=False)
    logger.debug("encode_texts: done shape=%s dtype=%s", getattr(out, "shape", None), out.dtype)
    return out
