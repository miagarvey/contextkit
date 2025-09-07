from pathlib import Path

ROOT = Path(".").resolve()
DIRS = {
    "packs": ROOT / "packs",
    "chats": ROOT / "chats",
    "art_sql": ROOT / "artifacts" / "sql",
    "art_code": ROOT / "artifacts" / "code",
    "art_text": ROOT / "artifacts" / "text",
    "schema": ROOT / "resources" / "schema",
    "data_manifests": ROOT / "resources" / "data_manifests",
    "index": ROOT / "index",
    "cfg": ROOT / ".contextkit",
}

for p in DIRS.values():
    p.mkdir(parents=True, exist_ok=True)
