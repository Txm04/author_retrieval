# app/embeddings/encoder.py
from sentence_transformers import SentenceTransformer
import torch, numpy as np
from typing import Tuple
from app.config import settings

def load_model(model_name: str = settings.EMBED_MODEL, device: str | None = settings.EMBED_DEVICE) -> Tuple[SentenceTransformer, str]:
    if device is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    model = SentenceTransformer(model_name, device=device)
    return model, device

def encode_texts(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    emb = model.encode(texts, convert_to_numpy=True)
    return emb.astype(np.float32, copy=False)
