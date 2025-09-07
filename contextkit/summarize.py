from __future__ import annotations
import os
from typing import Dict, Tuple
from contextkit.utils import est_tokens

# Heuristic fallback summarizer; replace with LLM if OPENAI_API_KEY provided.
def summarize_heuristic(body: str) -> str:
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    # Keep first N lines and code block headers
    head = lines[:30]
    return "\n".join(head)

def summarize_chat(front: Dict, body: str) -> Tuple[str, int]:
    # If OpenAI key is present, you could call into an LLM here (left as TODO).
    text = summarize_heuristic(body)
    return text, est_tokens(text)
