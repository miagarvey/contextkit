from __future__ import annotations
from pathlib import Path
from typing import List
import numpy as np

# Lazy import to avoid heavy startup
_model = None

def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed_texts(texts: List[str]) -> np.ndarray:
    m = _load_model()
    vecs = m.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return vecs.astype("float32")
