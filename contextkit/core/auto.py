from __future__ import annotations
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from contextkit.storage.faiss_store import search
from contextkit.core.utils import load_md, est_tokens
from contextkit.storage.index import connect, query as db_query
from contextkit.schema.schema_drift import check_pack_compatibility

class ContextComposer:
    """Orchestrates automatic context selection and composition using LLM intelligence."""
    
    def __init__(self, max_tokens: int = 8000, project: Optional[str] = None):
        self.max_tokens = max_tokens
        self.reserved_tokens = 500  # Reserve space for prompt and formatting
        self.available_tokens = max_tokens - self.reserved_tokens
        self.project = project
    
    def find_relevant_contexts(self, prompt: str, top_k: int = 15) -> List[Tuple[str, float]]:
        """Find potentially relevant ContextPacks using semantic search, filtered by project."""
        hits = search(prompt, top_k=top_k)
        
        # Filter to only ContextPacks (not raw chats) and by project if specified
        pack_hits = []
        conn = connect()
        
        for path, score in hits:
            if "/packs/" in path and path.endswith(".md"):
                # Check project filter
                if self.project:
                    rows = list(db_query(conn, "SELECT project FROM docs WHERE path=?", (path,)))
                    if rows and rows[0]["project"] != self.project:
                        continue
                pack_hits.append((path, score))
        
        conn.close()
        return pack_hits[:10]  # Return top 10 for LLM evaluation
    
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
        """Use multi-stage LLM evaluation to intelligently select and compose context."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except ImportError:
            raise ImportError("OpenAI package required for LLM ranking")
        
        # Stage 1: Context Pack Selection
        candidates_text = ""
        for i, candidate in enumerate(candidates):
            candidates_text += f"""
{i+1}. "{candidate['title']}" (Project: {candidate['project']})
   Summary: {candidate['summary']}
   Available artifacts: {candidate['artifacts']} code/SQL/data blocks
   Tables mentioned: {', '.join(candidate['tables']) if candidate['tables'] else 'None'}
"""
        
        selection_prompt = f"""You are a context selection assistant. Your job is to be VERY selective and only choose context that would genuinely help answer the user's question.

User's question: "{prompt}"

Available ContextPacks from previous conversations:
{candidates_text}

INSTRUCTIONS:
1. Only select ContextPacks if they contain information that would ACTUALLY help answer this specific question
2. Be conservative - it's better to select nothing than to include irrelevant context
3. Consider: Does this ContextPack contain relevant analysis, data patterns, code, or insights for this question?

Respond with ONLY the numbers of helpful ContextPacks (comma-separated), or "none" if no context would help.
Example responses: "1,3" or "2" or "none"
"""

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": selection_prompt}],
                max_tokens=50,
                temperature=0.1
            )
            
            selection_text = response.choices[0].message.content.strip().lower()
            
            if selection_text == "none":
                return []
            
            # Parse selection
            try:
                indices = [int(x.strip()) - 1 for x in selection_text.split(",")]
                selected_paths = [candidates[i]["path"] for i in indices if 0 <= i < len(candidates)]
                
                # Stage 2: Artifact Selection for selected ContextPacks
                return self._select_artifacts_for_contexts(client, prompt, selected_paths)
                
            except (ValueError, IndexError):
                # Fallback if parsing fails
                return [c["path"] for c in candidates[:2]]
                
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")
    
    def _select_artifacts_for_contexts(self, client, prompt: str, selected_paths: List[str]) -> List[str]:
        """Stage 2: For each selected ContextPack, determine what artifacts to include."""
        enhanced_paths = []
        
        for path in selected_paths:
            try:
                front, body = load_md(Path(path))
                artifacts = front.get('artifacts', [])
                
                if not artifacts:
                    enhanced_paths.append(path)
                    continue
                
                # Get artifact details
                artifact_details = []
                for i, artifact in enumerate(artifacts):
                    artifact_hash = artifact.get('hash', '')
                    artifact_kind = artifact.get('kind', 'unknown')
                    
                    # Load a preview of the artifact
                    artifact_content = self._load_artifact_by_hash(artifact_hash)
                    preview = artifact_content[:200] + "..." if artifact_content and len(artifact_content) > 200 else artifact_content or "Could not load"
                    
                    artifact_details.append(f"{i+1}. {artifact_kind.upper()}: {preview}")
                
                if artifact_details:
                    artifact_prompt = f"""For the ContextPack "{front.get('title', 'Unknown')}", determine which artifacts would help answer: "{prompt}"

Available artifacts:
{chr(10).join(artifact_details)}

Which artifacts would be helpful? Respond with numbers (comma-separated) or "none".
Be selective - only include artifacts that directly relate to the question."""

                    try:
                        artifact_response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": artifact_prompt}],
                            max_tokens=30,
                            temperature=0.1
                        )
                        
                        artifact_selection = artifact_response.choices[0].message.content.strip().lower()
                        
                        # Store artifact selection info with the path (we'll use this in compose_context)
                        if artifact_selection != "none":
                            try:
                                selected_artifact_indices = [int(x.strip()) - 1 for x in artifact_selection.split(",")]
                                # We'll pass this info through a modified path format
                                enhanced_paths.append(f"{path}|artifacts:{','.join(map(str, selected_artifact_indices))}")
                            except:
                                enhanced_paths.append(path)
                        else:
                            enhanced_paths.append(path)
                    except:
                        enhanced_paths.append(path)
                else:
                    enhanced_paths.append(path)
                    
            except Exception:
                enhanced_paths.append(path)
        
        return enhanced_paths
    
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
                        current_schema: Optional[Dict] = None,
                        project: Optional[str] = None) -> str:
    """Main entry point for automatic context composition with project filtering."""
    composer = ContextComposer(max_tokens=max_tokens, project=project)
    
    # Find relevant contexts (filtered by project if specified)
    candidates = composer.find_relevant_contexts(prompt, top_k=15)
    
    if not candidates:
        project_note = f" within project '{project}'" if project else ""
        return f"[CONTEXTKIT] No relevant context found{project_note}.\n\n{prompt}"
    
    # Use LLM to intelligently select contexts and artifacts
    selected_paths = composer.rank_contexts_with_llm(prompt, candidates)
    
    # Compose final context with selected artifacts
    return composer.compose_context(selected_paths, prompt, current_schema)
