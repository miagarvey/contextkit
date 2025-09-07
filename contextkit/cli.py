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
    front, body = load_md(path)
    banner = f"[CONTEXTKIT] Using pack {front.get('title')} | pack_hash={front.get('hash')} | schema_fp={front.get('schema_fingerprint')}"
    print(banner)
    if validate_schema:
        if validate_schema.startswith("postgres://") or validate_schema.startswith("postgresql://"):
            snap = introspect_postgres(validate_schema)
            current = fingerprint_schema_json(snap)
        else:
            import json as _json
            p = Path(validate_schema); current = fingerprint_schema_json(_json.loads(p.read_text(encoding='utf-8')))
        if current != front.get("schema_fingerprint"):
            print("[yellow][SCHEMA WARNING][/yellow] Current schema fingerprint differs; verify canonical definitions and SQL.")
    print("\n" + body)

if __name__ == "__main__":
    app()
