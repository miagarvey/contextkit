"""Chat-related CLI commands."""
import re
from pathlib import Path
from typing import Optional
import typer
from rich import print
from contextkit.paths import DIRS
from contextkit.core.utils import load_md, dump_md, extract_artifacts, hash_string, canonicalize_front, now_utc_iso
from contextkit.storage.index import rebuild_index
from contextkit.storage.faiss_store import build_faiss
from contextkit.core.summarize import summarize_chat


def save_chat_command(
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
            from contextkit.schema.schema_fp import introspect_postgres, save_schema_snapshot
            snap = introspect_postgres(schema)
            fp = save_schema_snapshot(snap, db_slug="default")
        else:
            # assume it is a path to a schema JSON
            import json as _json
            p = Path(schema)
            snap = _json.loads(p.read_text(encoding="utf-8"))
            from contextkit.schema.schema_fp import fingerprint_schema_json
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
    rebuild_index()
    build_faiss()


def summarize_command(path: Path):
    """Create a structured ContextPack from a chat."""
    from contextkit.core.utils import load_md, dump_md
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
    from contextkit.core.utils import hash_string, canonicalize_front
    canon = canonicalize_front(pack_front, ["project","title","schema_fingerprint","tables","artifacts"]).decode("utf-8")
    pack_hash = hash_string((canon + "\n" + pack_body).encode("utf-8").hex())
    pack_front["hash"] = pack_hash
    slug = re.sub(r"[^a-z0-9-]+", "-", pack_front["title"].lower()).strip("-")
    out = DIRS["packs"] / f"{slug}--{pack_hash[:12]}.md"
    out.write_text(dump_md(pack_front, pack_body), encoding="utf-8")
    print(f"[green]Saved pack[/green] {out}")
    
    # reindex
    rebuild_index()
    build_faiss()


def inject_command(
    path: Path, 
    validate_schema: Optional[str] = typer.Option(None, "--validate-schema", help="postgres://... or path to schema JSON")
):
    """Print a copy-pasteable pack with a small provenance banner."""
    from contextkit.core.utils import load_md
    from contextkit.schema.schema_fp import introspect_postgres, fingerprint_schema_json
    from contextkit.schema.schema_drift import check_pack_compatibility
    
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
