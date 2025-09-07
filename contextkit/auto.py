from __future__ import annotations
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from contextkit.faiss_store import search
from contextkit.utils import load_md, est_tokens
from contextkit.index import connect, query as db_query
from contextkit.schema_drift import check_pack_compatibility

class ContextComposer:
    """Orchestrates automatic context selection and composition."""
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.reserved_tokens = 500  # Reserve space for prompt and formatting
        self.available_tokens = max_tokens - self.reserved_tokens
    
    def find_relevant_contexts(self, prompt: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Find potentially relevant ContextPacks using semantic search."""
        hits = search(prompt, top_k=top_k)
        
        # Filter to only ContextPacks (not raw chats)
        pack_hits = []
        for path, score in hits:
            if "/packs/" in path and path.endswith(".md"):
                pack_hits.append((path, score))
        
        return pack_hits[:top_k//2]  # Take top half, focus on quality
    
    def rank_contexts_with_llm(self, prompt: str, candidates: List[Tuple[str, float]]) -> List[str]:
        """Use LLM to intelligently rank and select contexts."""
        if not candidates:
            return []
        
        # Load candidate summaries
        candidate_info = []
        for path, score in candidates:
            try:
                front, body = load_md(Path(path))
                candidate_info.append({
                    "path": path,
                    "title": front.get("title", "Unknown"),
                    "project": front.get("project", "Unknown"),
                    "tables": front.get("tables", []),
                    "artifacts": len(front.get("artifacts", [])),
                    "score": score,
                    "summary": body[:200] + "..." if len(body) > 200 else body
                })
            except Exception:
                continue
        
        if not candidate_info:
            return []
        
        # Try LLM ranking if OpenAI key available
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                return self._llm_rank_contexts(prompt, candidate_info)
            except Exception as e:
                print(f"[yellow]LLM ranking failed: {e}. Using heuristic ranking.[/yellow]")
        
        # Fallback: heuristic ranking
        return self._heuristic_rank_contexts(prompt, candidate_info)
    
    def _llm_rank_contexts(self, prompt: str, candidates: List[Dict]) -> List[str]:
        """Use OpenAI to rank contexts by relevance."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except ImportError:
            raise ImportError("OpenAI package required for LLM ranking")
        
        # Build ranking prompt
        candidates_text = ""
        for i, candidate in enumerate(candidates):
            candidates_text += f"""
{i+1}. {candidate['title']} (Project: {candidate['project']})
   Tables: {', '.join(candidate['tables']) if candidate['tables'] else 'None'}
   Artifacts: {candidate['artifacts']} code/SQL blocks
   Summary: {candidate['summary']}
"""
        
        ranking_prompt = f"""You are helping select the most relevant context for an LLM prompt.

User's new prompt: "{prompt}"

Available contexts:
{candidates_text}

Rank these contexts by relevance to the user's prompt. Consider:
1. Semantic similarity to the prompt topic
2. Overlapping data/tables that might be relevant  
3. Similar analytical approaches or code patterns
4. Complementary insights that could inform the new analysis

Respond with just the numbers of the most relevant contexts in order, separated by commas.
Example: "3,1,5" (if contexts 3, 1, and 5 are most relevant in that order)

Only include contexts that would actually help with this prompt. If none are relevant, respond with "none".
"""

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": ranking_prompt}],
                max_tokens=100,
                temperature=0.1
            )
            
            ranking_text = response.choices[0].message.content.strip().lower()
            
            if ranking_text == "none":
                return []
            
            # Parse ranking
            try:
                indices = [int(x.strip()) - 1 for x in ranking_text.split(",")]
                return [candidates[i]["path"] for i in indices if 0 <= i < len(candidates)]
            except (ValueError, IndexError):
                # Fallback if parsing fails
                return [c["path"] for c in candidates[:3]]
                
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")
    
    def _heuristic_rank_contexts(self, prompt: str, candidates: List[Dict]) -> List[str]:
        """Fallback heuristic ranking based on semantic score and recency."""
        # Sort by semantic score, take top 3
        sorted_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
        return [c["path"] for c in sorted_candidates[:3]]
    
    def compose_context(self, selected_paths: List[str], prompt: str, 
                       current_schema: Optional[Dict] = None) -> str:
        """Compose final context from selected ContextPacks."""
        if not selected_paths:
            return f"[CONTEXTKIT] No relevant context found.\n\n{prompt}"
        
        context_parts = []
        total_tokens = 0
        used_packs = []
        
        for path in selected_paths:
            try:
                front, body = load_md(Path(path))
                
                # Check schema compatibility if provided
                compatibility_note = ""
                if current_schema:
                    try:
                        compatibility, notes = check_pack_compatibility(Path(path), current_schema)
                        if compatibility == "breaking":
                            compatibility_note = " [SCHEMA WARNING: Breaking changes detected]"
                        elif compatibility == "compatible":
                            compatibility_note = " [SCHEMA: Compatible with changes]"
                    except Exception:
                        pass
                
                # Include key artifacts if space allows
                artifact_sections = []
                artifacts = front.get('artifacts', [])
                
                for artifact_hash in artifacts[:3]:  # Limit to top 3 artifacts
                    try:
                        artifact_content = self._load_artifact_by_hash(artifact_hash)
                        if artifact_content:
                            artifact_type = self._get_artifact_type(artifact_hash)
                            artifact_section = f"""
### Artifact ({artifact_type}):
```{artifact_type}
{artifact_content[:500]}{'...' if len(artifact_content) > 500 else ''}
```
"""
                            artifact_tokens = est_tokens(artifact_section)
                            if total_tokens + artifact_tokens < self.available_tokens * 0.7:  # Reserve 30% for other content
                                artifact_sections.append(artifact_section)
                    except Exception:
                        continue
                
                # Build context section
                artifacts_text = "".join(artifact_sections) if artifact_sections else ""
                pack_context = f"""
## Context: {front.get('title', 'Unknown')} (Project: {front.get('project', 'Unknown')}){compatibility_note}
{body}
{artifacts_text}
Artifacts available: {len(front.get('artifacts', []))} code/SQL blocks
Source: {front.get('source_chat_hash', 'Unknown')[:12]}...
"""
                
                # Check token budget
                section_tokens = est_tokens(pack_context)
                if total_tokens + section_tokens > self.available_tokens:
                    # Try to fit a truncated version without artifacts
                    truncated = f"""
## Context: {front.get('title', 'Unknown')} (Project: {front.get('project', 'Unknown')}){compatibility_note}
{body[:500]}...

[Truncated - full context available in {Path(path).name}]
"""
                    truncated_tokens = est_tokens(truncated)
                    if total_tokens + truncated_tokens <= self.available_tokens:
                        context_parts.append(truncated)
                        total_tokens += truncated_tokens
                        used_packs.append(Path(path).name)
                    break
                else:
                    context_parts.append(pack_context)
                    total_tokens += section_tokens
                    used_packs.append(Path(path).name)
                    
            except Exception as e:
                print(f"[yellow]Error loading context from {path}: {e}[/yellow]")
                continue
        
        # Build final context
        if not context_parts:
            return f"[CONTEXTKIT] No context could be loaded.\n\n{prompt}"
        
        header = f"[CONTEXTKIT] Auto-selected context from {len(used_packs)} ContextPack(s): {', '.join(used_packs)}"
        header += f"\nEstimated tokens: {total_tokens}/{self.max_tokens}\n"
        
        full_context = header + "\n" + "\n".join(context_parts) + f"\n\n[END CONTEXT]\n\n{prompt}"
        
        return full_context
    
    def _load_artifact_by_hash(self, artifact_hash: str) -> Optional[str]:
        """Load artifact content by hash from the artifacts directory."""
        from contextkit.paths import DIRS
        
        # Try different artifact directories
        for artifact_dir in [DIRS["art_sql"], DIRS["art_code"], DIRS["art_text"]]:
            for file_path in artifact_dir.glob(f"{artifact_hash}.*"):
                try:
                    return file_path.read_text(encoding="utf-8")
                except Exception:
                    continue
        return None
    
    def _get_artifact_type(self, artifact_hash: str) -> str:
        """Determine artifact type from file extension."""
        from contextkit.paths import DIRS
        
        for artifact_dir in [DIRS["art_sql"], DIRS["art_code"], DIRS["art_text"]]:
            for file_path in artifact_dir.glob(f"{artifact_hash}.*"):
                ext = file_path.suffix.lower()
                if ext == ".sql":
                    return "sql"
                elif ext == ".py":
                    return "python"
                elif ext == ".txt":
                    # Try to infer from content or return generic
                    return "text"
        return "unknown"

def auto_compose_context(prompt: str, max_tokens: int = 8000, 
                        current_schema: Optional[Dict] = None) -> str:
    """Main entry point for automatic context composition."""
    composer = ContextComposer(max_tokens=max_tokens)
    
    # Find relevant contexts
    candidates = composer.find_relevant_contexts(prompt, top_k=10)
    
    if not candidates:
        return f"[CONTEXTKIT] No relevant context found.\n\n{prompt}"
    
    # Rank contexts
    selected_paths = composer.rank_contexts_with_llm(prompt, candidates)
    
    # Compose final context
    return composer.compose_context(selected_paths, prompt, current_schema)
