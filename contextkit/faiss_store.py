from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import numpy as np
import json
import pickle
from sklearn.metrics.pairwise import cosine_similarity
from contextkit.paths import DIRS
from contextkit.index import connect, query

INDEX_PATH = DIRS["index"] / "sklearn_index.pkl"
META_PATH = DIRS["index"] / "sklearn_meta.json"

def build_faiss() -> None:
    """Build vector index from all documents using scikit-learn."""
    conn = connect()
    rows = list(query(conn, "SELECT path, kind, project, title, summary FROM docs"))
    texts = [f"{r['project']} | {r['title']} | {r['summary']}" for r in rows]
    from contextkit.embeds import embed_texts
    if not rows:
        return
    vecs = embed_texts(texts)
    
    # Save embeddings and metadata
    with open(INDEX_PATH, 'wb') as f:
        pickle.dump(vecs, f)
    
    META_PATH.write_text(json.dumps({"paths": [r["path"] for r in rows]}), encoding="utf-8")

def search(q: str, top_k: int = 5) -> List[Tuple[str, float]]:
    """Search for similar documents using cosine similarity."""
    if not INDEX_PATH.exists() or not META_PATH.exists():
        return []
    
    from contextkit.embeds import embed_texts
    
    # Load embeddings and metadata
    with open(INDEX_PATH, 'rb') as f:
        stored_embeddings = pickle.load(f)
    
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    
    # Get query embedding
    query_embedding = embed_texts([q])
    
    # Compute cosine similarities
    similarities = cosine_similarity(query_embedding, stored_embeddings)[0]
    
    # Get top-k results
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    out = []
    for i in top_indices:
        if similarities[i] > 0:  # Only include positive similarities
            out.append((meta["paths"][int(i)], float(similarities[i])))
    
    return out
