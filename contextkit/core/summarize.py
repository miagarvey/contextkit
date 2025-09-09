from __future__ import annotations
import os
from typing import Dict, Tuple, Optional
from contextkit.core.utils import est_tokens

def summarize_llm(front: Dict, body: str) -> str:
    """Use OpenAI to create a structured ContextPack summary."""
    try:
        import openai
        from openai import OpenAI
    except ImportError:
        raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Extract key info from front matter
    project = front.get("project", "unknown")
    title = front.get("title", "untitled")
    tables = front.get("tables_touched", [])
    artifacts = front.get("artifacts", [])
    
    # Build context about artifacts
    artifact_context = ""
    if artifacts:
        artifact_types = [a.get("kind", "unknown") for a in artifacts]
        artifact_context = f"\nArtifacts extracted: {', '.join(set(artifact_types))}"
    
    tables_context = ""
    if tables:
        tables_context = f"\nTables involved: {', '.join(tables)}"
    
    prompt = f"""Analyze this LLM chat session and create a structured summary for reuse in future sessions.

Project: {project}
Title: {title}{tables_context}{artifact_context}

Chat content:
{body[:4000]}...

Create a structured summary with these sections:
## Goal
Brief description of what this analysis accomplished

## Canonical Definitions  
Key business terms, metrics, or concepts defined (if any)

## Entities & Relationships
Important data relationships discovered (if any)

## Reusable SQL
Key SQL patterns or queries (reference by concept, not full code)

## Pinned Results
Important numbers, insights, or conclusions

## Pitfalls / Constraints
Data quality issues, limitations, or gotchas discovered

## Next Steps
Logical follow-up analyses or improvements

Keep each section concise and focused on reusable insights. If a section doesn't apply, write "None identified" rather than leaving it empty."""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[yellow]LLM summarization failed: {e}. Using heuristic fallback.[/yellow]")
        return summarize_heuristic(body)

def summarize_heuristic(body: str) -> str:
    """Heuristic fallback summarizer."""
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    # Keep first N lines and code block headers
    head = lines[:30]
    return "\n".join(head)

def summarize_chat(front: Dict, body: str) -> Tuple[str, int]:
    """Create a summary of the chat, using LLM if available."""
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if openai_key:
        try:
            text = summarize_llm(front, body)
        except Exception as e:
            print(f"[yellow]LLM summarization failed: {e}. Using heuristic fallback.[/yellow]")
            text = summarize_heuristic(body)
    else:
        text = summarize_heuristic(body)
    
    return text, est_tokens(text)
