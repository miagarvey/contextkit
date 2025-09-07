from __future__ import annotations
from typing import Dict, Any
from pathlib import Path
import json, re
from blake3 import blake3
from contextkit.paths import DIRS

def _normalize_ident(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).lower()

def fingerprint_schema_json(schema: Dict[str, Any]) -> str:
    # sort keys for stability
    def norm(obj):
        if isinstance(obj, dict):
            return {k: norm(obj[k]) for k in sorted(obj)}
        if isinstance(obj, list):
            return [norm(x) for x in obj]
        if isinstance(obj, str):
            return _normalize_ident(obj)
        return obj
    normed = norm(schema)
    data = json.dumps(normed, separators=(',',':')).encode('utf-8')
    return f"blake3:{blake3(data).hexdigest()}"

def introspect_postgres(conn_str: str) -> Dict[str, Any]:
    import psycopg
    out = {}
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_schema, table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema NOT IN ('information_schema','pg_catalog')
                ORDER BY table_schema, table_name, ordinal_position
            """)
            for sch, tbl, col, typ in cur.fetchall():
                out.setdefault(sch, {}).setdefault(tbl, {})[col] = typ
    return out

def save_schema_snapshot(schema: Dict[str, Any], db_slug: str) -> str:
    fp = fingerprint_schema_json(schema)
    path = DIRS["schema"] / db_slug / f"{fp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return fp
