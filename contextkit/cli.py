from __future__ import annotations
import os, re, json, shutil, subprocess
from pathlib import Path
from typing import Optional, List, Dict
import typer
from rich import print, box
from rich.table import Table
from contextkit.paths import DIRS
from contextkit.utils import load_md, dump_md, extract_artifacts, hash_string, canonicalize_front, now_utc_iso
from contextkit.index import rebuild_index, connect, query
from contextkit.faiss_store import build_faiss, search
from contextkit.schema_fp import introspect_postgres, save_schema_snapshot
from contextkit.summarize import summarize_chat
from contextkit.auto import auto_compose_context

app = typer.Typer(help="ContextKit CLI (MVP)")

@app.command()
def index(rebuild: bool = typer.Option(True, help="Rebuild SQLite + FAISS indices")):
    """Rebuild indices."""
    if rebuild:
        rebuild_index()
        build_faiss()
        print("[green]Index rebuilt.[/green]")

@app.command()
def schema(
    action: str = typer.Argument(..., help="fingerprint"),
    from_: Optional[str] = typer.Option(None, "--from", help="postgres://... or path to JSON"),
    ddl: Optional[Path] = typer.Option(None, help="(future) path to DDL"),
    db_slug: str = typer.Option("default", help="Folder name under resources/schema"),
):
    """Schema operations: fingerprint a DB and store snapshot."""
    if action != "fingerprint":
        raise typer.Exit(code=1)
    if not from_:
        print("[red]--from is required[/red]"); raise typer.Exit(code=1)
    if from_.startswith("postgres://") or from_.startswith("postgresql://"):
        schema = introspect_postgres(from_)
    else:
        # treat as JSON file
        p = Path(from_)
        schema = json.loads(p.read_text(encoding="utf-8"))
    fp = save_schema_snapshot(schema, db_slug=db_slug)
    print(f"[green]Saved schema snapshot with fingerprint[/green] {fp}")

@app.command("save-chat")
def save_chat(
    project: str = typer.Option(...),
    title: str = typer.Option(...),
    from_: Path = typer.Option(..., "--from", help="Path to markdown chat file"),
    schema: Optional[str] = typer.Option(None, help="postgres://... or path to schema JSON"),
    tags: Optional[str] = typer.Option(None, help="comma-separated"),
):
    """Ingest a chat, extract artifacts, compute hashes, update index."""
    front, body = load_md(from_)
    front.update({
        "type": "chat",
        "project": project,
        "title": title,
        "created_utc": front.get("created_utc") or now_utc_iso(),
    })
    if tags:
        front["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    # artifacts
    arts = []
    for lang, code in extract_artifacts(body):
        if lang in ("sql",):
            subdir = DIRS["art_sql"]
            ext = ".sql"
        elif lang in ("python", "py"):
            subdir = DIRS["art_code"]
            ext = ".py"
        else:
            subdir = DIRS["art_text"]
            ext = ".txt"
        h = hash_string(code)
        path = subdir / f"{h}{ext}"
        path.write_text(code, encoding="utf-8")
        arts.append({"kind": lang, "path": str(path), "hash": h})
    if arts:
        front["artifacts"] = arts
    # schema
    if schema:
        if schema.startswith("postgres://") or schema.startswith("postgresql://") or schema.startswith("postgis://"):
            from contextkit.schema_fp import introspect_postgres, save_schema_snapshot
            snap = introspect_postgres(schema)
            fp = save_schema_snapshot(snap, db_slug="default")
        else:
            # assume it is a path to a schema JSON
            import json as _json
            p = Path(schema)
            snap = _json.loads(p.read_text(encoding="utf-8"))
            from contextkit.schema_fp import fingerprint_schema_json
            fp = fingerprint_schema_json(snap)
        front["schema_fingerprint"] = fp
    # compute chat hash
    canon = canonicalize_front(front, ["project","title","tables_touched","tags","schema_fingerprint"]).decode("utf-8")
    chat_hash = hash_string((canon + "\n" + body).encode("utf-8").hex())
    front["hash"] = chat_hash
    # write chat file
    slug = re.sub(r"[^a-z0-9-]+", "-", title.lower()).strip("-")
    # Extract date from ISO string (YYYY-MM-DD format)
    date_part = front['created_utc'][:10] if isinstance(front['created_utc'], str) else front['created_utc'].isoformat()[:10]
    out = DIRS["chats"] / f"{date_part}--{slug}.md"
    out.write_text(dump_md(front, body), encoding="utf-8")
    print(f"[green]Saved chat[/green] {out}")
    # update index
    rebuild_index(); build_faiss()

@app.command()
def summarize(path: Path):
    """Create a structured ContextPack from a chat."""
    from contextkit.utils import load_md, dump_md
    front, body = load_md(path)
    text, tokens = summarize_chat(front, body)
    pack_front = {
        "type": "contextpack",
        "project": front.get("project"),
        "title": front.get("title"),
        "created_utc": now_utc_iso(),
        "source_chat_hash": front.get("hash"),
        "schema_fingerprint": front.get("schema_fingerprint"),
        "tables": front.get("tables_touched") or [],
        "artifacts": [a.get("hash") for a in front.get("artifacts", [])],
        "tokens_estimate": tokens,
    }
    # simple body scaffold
    pack_body = f"""## Goal
Summarized from chat.

## Canonical Definitions
- (fill)

## Entities & Relationships
- (fill)

## Reusable SQL
```
-- insert key SQL snippets by artifact hash
```

## Pinned Results
- (fill)

## Pitfalls / Constraints
- (fill)

## Next Steps
- (fill)
"""
    from contextkit.utils import hash_string, canonicalize_front
    canon = canonicalize_front(pack_front, ["project","title","schema_fingerprint","tables","artifacts"]).decode("utf-8")
    pack_hash = hash_string((canon + "\n" + pack_body).encode("utf-8").hex())
    pack_front["hash"] = pack_hash
    slug = re.sub(r"[^a-z0-9-]+", "-", pack_front["title"].lower()).strip("-")
    out = DIRS["packs"] / f"{slug}--{pack_hash[:12]}.md"
    out.write_text(dump_md(pack_front, pack_body), encoding="utf-8")
    print(f"[green]Saved pack[/green] {out}")
    # reindex
    rebuild_index(); build_faiss()

@app.command()
def find(query: List[str] = typer.Argument(...), project: Optional[str] = typer.Option(None), tables: Optional[str] = typer.Option(None), top_k: int = 5):
    q = " ".join(query)
    hits = search(q, top_k=top_k)
    if not hits:
        print("[yellow]No vector index yet or no results. Run: ctx index[/yellow]")
        raise typer.Exit()
    tbl = Table(title=f"Results for: {q}", box=box.SIMPLE)
    tbl.add_column("score"); tbl.add_column("path"); tbl.add_column("title"); tbl.add_column("project")
    conn = connect()
    from contextkit.index import query as db_query
    for path, score in hits:
        row = next(db_query(conn, "SELECT title, project FROM docs WHERE path=?", (path,)), None)
        tbl.add_row(f"{score:.3f}", path, row["title"] if row else "", row["project"] if row else "")
    print(tbl)

@app.command()
def show(path: Path):
    front, body = load_md(path)
    print(json.dumps(front, indent=2))
    print("\n---\n")
    print(body[:1000] + ("\n..." if len(body) > 1000 else ""))

@app.command()
def inject(path: Path, validate_schema: Optional[str] = typer.Option(None, "--validate-schema", help="postgres://... or path to schema JSON")):
    """Print a copy-pasteable pack with a small provenance banner. If validate-schema is provided, will print a simple warning on mismatch."""
    from contextkit.utils import load_md
    from contextkit.schema_fp import introspect_postgres, fingerprint_schema_json
    from contextkit.schema_drift import check_pack_compatibility
    
    front, body = load_md(path)
    banner = f"[CONTEXTKIT] Using pack {front.get('title')} | pack_hash={front.get('hash')} | schema_fp={front.get('schema_fingerprint')}"
    print(banner)
    
    if validate_schema:
        if validate_schema.startswith("postgres://") or validate_schema.startswith("postgresql://"):
            current_schema = introspect_postgres(validate_schema)
        else:
            import json as _json
            p = Path(validate_schema)
            current_schema = _json.loads(p.read_text(encoding='utf-8'))
        
        compatibility, notes = check_pack_compatibility(path, current_schema)
        
        if compatibility == "identical":
            print("[green][SCHEMA OK][/green] Schema fingerprints match exactly")
        elif compatibility == "compatible":
            print("[yellow][SCHEMA COMPATIBLE][/yellow] Schema has backward-compatible changes")
            for note in notes[:3]:  # Show first 3 changes
                print(f"  {note}")
        elif compatibility == "breaking":
            print("[red][SCHEMA WARNING][/red] Breaking schema changes detected")
            for note in notes[:5]:  # Show first 5 changes
                print(f"  {note}")
        else:
            print("[yellow][SCHEMA UNKNOWN][/yellow] Cannot determine compatibility")
            for note in notes:
                print(f"  {note}")
    
    print("\n" + body)

@app.command("schema-drift")
def schema_drift(
    action: str = typer.Argument(..., help="scan | check"),
    current_schema: Optional[str] = typer.Option(None, "--current", help="postgres://... or path to schema JSON"),
    pack_path: Optional[Path] = typer.Option(None, "--pack", help="Path to specific pack to check")
):
    """Schema drift detection and analysis."""
    from contextkit.schema_fp import introspect_postgres
    from contextkit.schema_drift import scan_packs_for_drift, check_pack_compatibility
    
    if action == "scan":
        if not current_schema:
            print("[red]--current is required for scan[/red]")
            raise typer.Exit(code=1)
        
        # Get current schema
        if current_schema.startswith("postgres://") or current_schema.startswith("postgresql://"):
            schema = introspect_postgres(current_schema)
        else:
            import json as _json
            p = Path(current_schema)
            schema = _json.loads(p.read_text(encoding='utf-8'))
        
        results = scan_packs_for_drift(schema)
        
        if not results:
            print("[yellow]No ContextPacks found to scan[/yellow]")
            return
        
        # Group by compatibility level
        compatible = []
        breaking = []
        unknown = []
        identical = []
        
        for pack_name, (compatibility, notes) in results.items():
            if compatibility == "identical":
                identical.append(pack_name)
            elif compatibility == "compatible":
                compatible.append((pack_name, notes))
            elif compatibility == "breaking":
                breaking.append((pack_name, notes))
            else:
                unknown.append((pack_name, notes))
        
        print(f"\n[bold]Schema Compatibility Scan Results[/bold]")
        print(f"Scanned {len(results)} ContextPacks\n")
        
        if identical:
            print(f"[green]✅ Identical ({len(identical)})[/green]")
            for pack in identical:
                print(f"  {pack}")
            print()
        
        if compatible:
            print(f"[yellow]⚠️  Compatible with changes ({len(compatible)})[/yellow]")
            for pack, notes in compatible:
                print(f"  {pack}")
                for note in notes[:2]:  # Show first 2 changes
                    print(f"    {note}")
            print()
        
        if breaking:
            print(f"[red]❌ Breaking changes ({len(breaking)})[/red]")
            for pack, notes in breaking:
                print(f"  {pack}")
                for note in notes[:3]:  # Show first 3 changes
                    print(f"    {note}")
            print()
        
        if unknown:
            print(f"[dim]❓ Unknown ({len(unknown)})[/dim]")
            for pack, notes in unknown:
                print(f"  {pack}: {notes[0] if notes else 'No details'}")
    
    elif action == "check":
        if not pack_path or not current_schema:
            print("[red]Both --pack and --current are required for check[/red]")
            raise typer.Exit(code=1)
        
        # Get current schema
        if current_schema.startswith("postgres://") or current_schema.startswith("postgresql://"):
            schema = introspect_postgres(current_schema)
        else:
            import json as _json
            p = Path(current_schema)
            schema = _json.loads(p.read_text(encoding='utf-8'))
        
        compatibility, notes = check_pack_compatibility(pack_path, schema)
        
        print(f"\n[bold]Schema Compatibility Check: {pack_path.name}[/bold]")
        print(f"Compatibility: [{'green' if compatibility == 'identical' else 'yellow' if compatibility == 'compatible' else 'red'}]{compatibility.upper()}[/]")
        print("\nDetails:")
        for note in notes:
            print(f"  {note}")
    
    else:
        print("[red]Unknown action. Use 'scan' or 'check'[/red]")
        raise typer.Exit(code=1)

@app.command()
def auto(
    prompt: List[str] = typer.Argument(..., help="Your prompt for the LLM"),
    max_tokens: int = typer.Option(8000, help="Maximum tokens for context (3000, 8000, 16000)"),
    schema: Optional[str] = typer.Option(None, "--schema", help="postgres://... or path to schema JSON for compatibility checking"),
    project: Optional[str] = typer.Option(None, help="Filter contexts to specific project"),
    copy: bool = typer.Option(False, "--copy", help="Copy result to clipboard (requires pbcopy/xclip)")
):
    """Automatically compose relevant context for your prompt."""
    user_prompt = " ".join(prompt)
    
    # Get current schema if provided
    current_schema = None
    if schema:
        try:
            if schema.startswith("postgres://") or schema.startswith("postgresql://"):
                from contextkit.schema_fp import introspect_postgres
                current_schema = introspect_postgres(schema)
            else:
                import json as _json
                p = Path(schema)
                current_schema = _json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[yellow]Warning: Could not load schema: {e}[/yellow]")
    
    # Compose context
    try:
        composed_context = auto_compose_context(
            prompt=user_prompt,
            max_tokens=max_tokens,
            current_schema=current_schema
        )
        
        print(composed_context)
        
        # Copy to clipboard if requested
        if copy:
            try:
                import subprocess
                import platform
                
                if platform.system() == "Darwin":  # macOS
                    subprocess.run(["pbcopy"], input=composed_context.encode(), check=True)
                    print(f"\n[green]✓ Copied to clipboard[/green]")
                elif platform.system() == "Linux":
                    subprocess.run(["xclip", "-selection", "clipboard"], input=composed_context.encode(), check=True)
                    print(f"\n[green]✓ Copied to clipboard[/green]")
                else:
                    print(f"\n[yellow]Clipboard copy not supported on {platform.system()}[/yellow]")
            except Exception as e:
                print(f"\n[yellow]Could not copy to clipboard: {e}[/yellow]")
                
    except Exception as e:
        print(f"[red]Error composing context: {e}[/red]")
        print(f"[yellow]Fallback: No context available for prompt[/yellow]")
        print(f"\n{user_prompt}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
