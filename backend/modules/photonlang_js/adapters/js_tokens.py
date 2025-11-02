from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Tuple
from backend.modules.photonlang.ir import TransformOptions, TransformResult

_HERE = Path(__file__).resolve().parent
_MAP_PATH = _HERE.parent / "javascript_token_map.json"

def _load_map() -> Dict[str, Dict[str, str]]:
    if _MAP_PATH.exists():
        return json.loads(_MAP_PATH.read_text(encoding="utf-8"))
    return {"keywords": {}, "operators": {}, "punctuation": {}}

# Very conservative string/comment skipper (no regex-literal handling yet).
_STR_RE = re.compile(
    r"""
    (?P<sq>'([^\\']|\\.)*')|
    (?P<dq>"([^\\"]|\\.)*")|
    (?P<bq>`([^\\`]|\\.)*`)|
    (?P<sl>//[^\n]*$)|
    (?P<ml>/\*.*?\*/ )
    """, re.VERBOSE | re.DOTALL | re.MULTILINE
)

def _build_replacements(mapping: Dict[str, str]) -> Tuple[re.Pattern, Dict[str, str]]:
    # Sort by length desc to avoid partial overlaps, escape for regex
    items = sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True)
    if not items:
        return re.compile(r"$^"), {}
    pat = "|".join(re.escape(k) for k, _ in items)
    return re.compile(pat), dict(items)

def _apply_replacements(code: str, repl_re: re.Pattern, table: Dict[str, str]) -> str:
    return repl_re.sub(lambda m: table[m.group(0)], code)

def _transform(src: str, table: Dict[str, Dict[str, str]], *, to_photon: bool) -> str:
    # Choose mapping direction
    ops = table.get("operators", {})
    punct = table.get("punctuation", {})
    pairs = {}
    pairs.update(ops)
    pairs.update(punct)
    if not to_photon:
        # invert
        pairs = {v: k for k, v in pairs.items()}

    repl_re, table1 = _build_replacements(pairs)

    out = []
    i = 0
    for m in _STR_RE.finditer(src):
        # transform plain chunk before the matched string/comment
        out.append(_apply_replacements(src[i:m.start()], repl_re, table1))
        # keep the matched region verbatim
        out.append(m.group(0))
        i = m.end()
    out.append(_apply_replacements(src[i:], repl_re, table1))
    return "".join(out)

def expand_text_js(src: str, *, options: TransformOptions | None = None) -> TransformResult:
    """Expand Photon-like JS → plain JS (operators/punct only for now)."""
    tbl = _load_map()
    text = _transform(src, tbl, to_photon=False)
    return TransformResult(text=text)

def compress_text_js(src: str, *, options: TransformOptions | None = None) -> TransformResult:
    """Compress JS → Photon-like JS glyph tokens (operators/punct only)."""
    tbl = _load_map()
    text = _transform(src, tbl, to_photon=True)
    return TransformResult(text=text)