from __future__ import annotations
import re, json, orjson, hashlib, datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from blake3 import blake3
from ruamel.yaml import YAML
import tiktoken

yaml = YAML()
yaml.preserve_quotes = True
yaml.width = 1000

FRONT_RE = re.compile(r'^---\n(.*?)\n---\n', re.S)

def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

def normalize_newlines(s: str) -> str:
    return s.replace('\r\n','\n').replace('\r','\n')

def load_md(path: Path) -> Tuple[Dict, str]:
    txt = normalize_newlines(path.read_text(encoding="utf-8"))
    m = FRONT_RE.match(txt)
    if m:
        front = yaml.load(m.group(1)) or {}
        body = txt[m.end():]
    else:
        front, body = {}, txt
    return front, body

def dump_md(front: Dict, body: str) -> str:
    from io import StringIO
    buf = StringIO()
    yaml.dump(front or {}, buf)
    return f"---\n{buf.getvalue()}---\n{body}"

def est_tokens(s: str, model: str = "gpt-4o-mini") -> int:
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(s))
    except Exception:
        return max(1, len(s)//4)

def hash_bytes(b: bytes) -> str:
    return f"blake3:{blake3(b).hexdigest()}"

def hash_string(s: str) -> str:
    return hash_bytes(s.encode('utf-8'))

def canonicalize_front(front: Dict, include_keys: List[str]) -> bytes:
    data = {k: front.get(k) for k in include_keys if k in front}
    return orjson.dumps(data, option=orjson.OPT_SORT_KEYS)

CODE_FENCE = re.compile(r"```(\w+)?\n(.*?)\n```", re.S)

def extract_artifacts(md_body: str) -> List[Tuple[str, str]]:
    # returns list of (lang, code)
    out = []
    for m in CODE_FENCE.finditer(md_body):
        lang = (m.group(1) or "text").lower()
        code = m.group(2)
        out.append((lang, code))
    return out
