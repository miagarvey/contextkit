from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterable
import sqlite3, json, os
from contextkit.paths import DIRS
from contextkit.core.utils import load_md, extract_artifacts, hash_string, est_tokens
import numpy as np

# Minimal index schema
SCHEMA = [
    """CREATE TABLE IF NOT EXISTS docs (
        id INTEGER PRIMARY KEY,
        kind TEXT,                  -- chat | pack | artifact | schema
        path TEXT UNIQUE,
        project TEXT,
        title TEXT,
        summary TEXT,
        tables TEXT,                -- JSON array
        tags TEXT,                  -- JSON array
        fingerprint TEXT,           -- schema fingerprint if any
        content_hash TEXT,
        created_utc TEXT
    );""",
    """CREATE INDEX IF NOT EXISTS idx_docs_project ON docs(project);"""
]

def db_path() -> Path:
    return DIRS["index"] / "meta.db"

def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    for stmt in SCHEMA:
        conn.execute(stmt)
    conn.commit()
    return conn

def upsert_doc(conn: sqlite3.Connection, rec: Dict[str, Any]):
    cols = ",".join(rec.keys())
    placeholders = ",".join("?" for _ in rec)
    updates = ",".join(f"{k}=excluded.{k}" for k in rec.keys() if k not in ("id","path"))
    sql = f"INSERT INTO docs ({cols}) VALUES ({placeholders}) ON CONFLICT(path) DO UPDATE SET {updates};"
    conn.execute(sql, tuple(rec.values()))

def query(conn: sqlite3.Connection, q: str, args: Iterable = ()):
    cur = conn.execute(q, args)
    cols = [c[0] for c in cur.description]
    for row in cur.fetchall():
        yield dict(zip(cols, row))

def rebuild_index() -> None:
    conn = connect()
    for base, kind in [(DIRS["chats"], "chat"), (DIRS["packs"], "pack")]:
        for p in base.glob("**/*.md"):
            front, body = load_md(p)
            # Convert created_utc to string if it's not already
            created_utc = front.get("created_utc")
            if created_utc and not isinstance(created_utc, str):
                # Handle TimeStamp objects or datetime objects
                if hasattr(created_utc, 'isoformat'):
                    created_utc = created_utc.isoformat()
                else:
                    created_utc = str(created_utc)
            
            rec = {
                "kind": kind,
                "path": str(p),
                "project": front.get("project"),
                "title": front.get("title"),
                "summary": front.get("summary") or body[:500],
                "tables": json.dumps(front.get("tables_touched") or front.get("tables") or []),
                "tags": json.dumps(front.get("tags") or []),
                "fingerprint": front.get("schema_fingerprint"),
                "content_hash": front.get("hash") or "",
                "created_utc": created_utc,
            }
            upsert_doc(conn, rec)
    conn.commit()
    conn.close()
