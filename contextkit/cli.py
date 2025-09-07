from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, List
import typer
from rich import print, box
from rich.table import Table
from contextkit.storage.index import rebuild_index, connect, query
from contextkit.storage.faiss_store import build_faiss, search
from contextkit.schema.schema_fp import introspect_postgres, save_schema_snapshot
from contextkit.core.auto import auto_compose_context
from contextkit.commands.chat_commands import save_chat_command, summarize_command, inject_command
from contextkit.core.utils import load_md

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
    save_chat_command(project, title, from_, schema, tags)

@app.command()
def summarize(path: Path):
    """Create a structured ContextPack from a chat."""
    summarize_command(path)

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
    from contextkit.storage.index import query as db_query
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
    """Print a copy-pasteable pack with a small provenance banner."""
    inject_command(path, validate_schema)

@app.command("schema-drift")
def schema_drift(
    action: str = typer.Argument(..., help="scan | check"),
    current_schema: Optional[str] = typer.Option(None, "--current", help="postgres://... or path to schema JSON"),
    pack_path: Optional[Path] = typer.Option(None, "--pack", help="Path to specific pack to check")
):
    """Schema drift detection and analysis."""
    from contextkit.schema.schema_fp import introspect_postgres
    from contextkit.schema.schema_drift import scan_packs_for_drift, check_pack_compatibility
    
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
                from contextkit.schema.schema_fp import introspect_postgres
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

@app.command()
def web(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(True, help="Enable auto-reload for development")
):
    """Start the ContextKit web interface."""
    try:
        import uvicorn
        from contextkit.web import app as web_app
        
        print(f"[green]Starting ContextKit web interface...[/green]")
        print(f"[blue]Open your browser to: http://localhost:{port}[/blue]")
        
        uvicorn.run(
            "contextkit.web:app",
            host=host,
            port=port,
            reload=reload
        )
    except ImportError:
        print("[red]FastAPI and uvicorn are required for the web interface.[/red]")
        print("Install with: pip install fastapi uvicorn")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        print("\n[yellow]Web server stopped.[/yellow]")

if __name__ == "__main__":
    app()
