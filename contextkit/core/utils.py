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

# Language mappings for better categorization
LANG_MAPPINGS = {
    'py': 'python',
    'js': 'javascript', 
    'ts': 'typescript',
    'sh': 'shell',
    'bash': 'shell',
    'zsh': 'shell',
    'r': 'r',
    'scala': 'scala',
    'java': 'java',
    'go': 'go',
    'rust': 'rust',
    'cpp': 'cpp',
    'c': 'c',
    'yaml': 'yaml',
    'yml': 'yaml',
    'json': 'json',
    'xml': 'xml',
    'html': 'html',
    'css': 'css',
    'dockerfile': 'dockerfile',
    'makefile': 'makefile'
}

def normalize_language(lang: str) -> str:
    """Normalize language identifiers."""
    if not lang:
        return "text"
    lang = lang.lower().strip()
    return LANG_MAPPINGS.get(lang, lang)

def extract_metadata_from_code(lang: str, code: str) -> Dict:
    """Extract metadata from code blocks."""
    metadata = {
        "line_count": len(code.splitlines()),
        "char_count": len(code),
        "has_comments": False,
        "complexity_indicators": []
    }
    
    # Detect comments
    comment_patterns = {
        'sql': [r'--', r'/\*.*?\*/'],
        'python': [r'#', r'""".*?"""', r"'''.*?'''"],
        'javascript': [r'//', r'/\*.*?\*/'],
        'typescript': [r'//', r'/\*.*?\*/'],
        'shell': [r'#'],
        'r': [r'#'],
        'yaml': [r'#'],
        'css': [r'/\*.*?\*/'],
        'html': [r'<!--.*?-->']
    }
    
    if lang in comment_patterns:
        for pattern in comment_patterns[lang]:
            if re.search(pattern, code, re.DOTALL):
                metadata["has_comments"] = True
                break
    
    # Language-specific complexity indicators
    if lang == 'sql':
        if re.search(r'\bJOIN\b', code, re.IGNORECASE):
            metadata["complexity_indicators"].append("joins")
        if re.search(r'\bWITH\b', code, re.IGNORECASE):
            metadata["complexity_indicators"].append("cte")
        if re.search(r'\bWINDOW\b', code, re.IGNORECASE):
            metadata["complexity_indicators"].append("window_functions")
        if re.search(r'\bCASE\b', code, re.IGNORECASE):
            metadata["complexity_indicators"].append("conditional_logic")
        
        # Extract table references
        table_matches = re.findall(r'\bFROM\s+(\w+)', code, re.IGNORECASE)
        join_matches = re.findall(r'\bJOIN\s+(\w+)', code, re.IGNORECASE)
        metadata["tables_referenced"] = list(set(table_matches + join_matches))
    
    elif lang == 'python':
        if re.search(r'\bimport\b|\bfrom\b.*\bimport\b', code):
            metadata["complexity_indicators"].append("imports")
        if re.search(r'\bdef\b|\bclass\b', code):
            metadata["complexity_indicators"].append("definitions")
        if re.search(r'\bfor\b|\bwhile\b', code):
            metadata["complexity_indicators"].append("loops")
        if re.search(r'\btry\b|\bexcept\b', code):
            metadata["complexity_indicators"].append("error_handling")
        
        # Extract imports
        import_matches = re.findall(r'(?:from\s+(\w+)|import\s+(\w+))', code)
        imports = [m[0] or m[1] for m in import_matches]
        metadata["imports"] = list(set(imports))
    
    return metadata

def extract_artifacts(md_body: str) -> List[Tuple[str, str]]:
    """Extract code artifacts with enhanced metadata support."""
    out = []
    for m in CODE_FENCE.finditer(md_body):
        raw_lang = m.group(1) or "text"
        lang = normalize_language(raw_lang)
        code = m.group(2).strip()
        
        # Skip empty code blocks
        if not code:
            continue
            
        out.append((lang, code))
    
    return out

def extract_artifacts_with_metadata(md_body: str) -> List[Dict]:
    """Extract artifacts with full metadata."""
    artifacts = []
    for m in CODE_FENCE.finditer(md_body):
        raw_lang = m.group(1) or "text"
        lang = normalize_language(raw_lang)
        code = m.group(2).strip()
        
        # Skip empty code blocks
        if not code:
            continue
        
        metadata = extract_metadata_from_code(lang, code)
        
        artifact = {
            "kind": lang,
            "raw_lang": raw_lang,
            "code": code,
            "hash": hash_string(code),
            "metadata": metadata
        }
        
        artifacts.append(artifact)
    
    return artifacts
