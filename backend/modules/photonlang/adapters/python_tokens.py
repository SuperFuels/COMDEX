from __future__ import annotations

import io
import json
import re
import tokenize
from pathlib import Path
from typing import Dict, Iterable


# --- brace sentinels + token-level masking (protect only real code braces) ---
import tokenize
from tokenize import TokenInfo

_PH_L = "__PH_LBRACE__"
_PH_R = "__PH_RBRACE__"

# 1) at top of file (with your imports/helpers)
# ------------------------------------------------------------------------------
# Brace sentinels (protect during compress; restore after expand)
# ------------------------------------------------------------------------------
_PH_DBL_L = "__PH_DBL_LBRACE__"   # protects "{{"
_PH_DBL_R = "__PH_DBL_RBRACE__"   # protects "}}"
_PH_L     = "__PH_LBRACE__"       # protects "{"
_PH_R     = "__PH_RBRACE__"       # protects "}"


# ──────────────────────────────────────────────────────────────────────────────
# Map loader (robust to legacy paths/keys)
# ──────────────────────────────────────────────────────────────────────────────

def _load_token_map() -> Dict[str, Dict[str, str]]:
    base = Path(__file__).resolve().parents[1]  # .../photonlang
    candidates = [
        base / "python_token_map.json",                 # preferred
        base / "photonlang" / "python_token_map.json",  # legacy/misplaced
    ]
    data: Dict[str, Dict[str, str]] = {}
    for p in candidates:
        try:
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                break
        except Exception:
            continue
    keywords = data.get("keywords") or {}
    operators = data.get("operators") or {}
    punct     = data.get("punct") or data.get("punctuation") or {}

    for sec_name, sec_map in (("keywords", keywords), ("operators", operators), ("punct", punct)):
        if not isinstance(sec_map, dict):
            raise ValueError(f"python_token_map.json: section '{sec_name}' must be an object")
        for k, v in sec_map.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValueError(f"python_token_map.json: '{sec_name}' must map str->str")
    return {"keywords": keywords, "operators": operators, "punct": punct}

TOKEN_TO_GLYPH: Dict[str, Dict[str, str]] = _load_token_map()
KW_MAP:  Dict[str, str] = TOKEN_TO_GLYPH["keywords"]
OP_MAP:  Dict[str, str] = TOKEN_TO_GLYPH["operators"]
PCT_MAP: Dict[str, str] = TOKEN_TO_GLYPH["punct"]

# Reverse maps (glyph -> token)
G2KW:  Dict[str, str] = {v: k for k, v in KW_MAP.items()}
G2OP:  Dict[str, str] = {v: k for k, v in OP_MAP.items()}
G2PCT: Dict[str, str] = {v: k for k, v in PCT_MAP.items()}

# Operators ∪ punctuation as one OP-like family
OPLIKE_FORWARD: Dict[str, str] = {**OP_MAP, **PCT_MAP}   # token -> glyph
G2OPLIKE: Dict[str, str]       = {**G2OP,  **G2PCT}      # glyph -> token
_OPLIKE_GLYPHS_BY_LEN = sorted(G2OPLIKE.keys(), key=len, reverse=True)

# ⚠️ derive AFTER maps exist
_PY_KEYWORDS = set(KW_MAP.keys())

# Exclude curlies from compression even if accidentally present in JSON
_OP_TOKENS = {k for k in OPLIKE_FORWARD.keys() if k not in {"{", "}"}}

_PY_KEYWORDS = set(KW_MAP.keys())
_OP_TOKENS   = set(OPLIKE_FORWARD.keys())

# Quick scan for any code-glyph
GLYPH_TO_TOKEN: Dict[str, str] = {}
for d in (KW_MAP, OP_MAP, PCT_MAP):
    for tok, gly in d.items():
        GLYPH_TO_TOKEN[gly] = tok
_glyph_tokens_sorted = sorted(GLYPH_TO_TOKEN.keys(), key=len, reverse=True)
_ALL_GLYPH_RE = re.compile("|".join(map(re.escape, _glyph_tokens_sorted))) if _glyph_tokens_sorted else None
_CODE_GLYPH_RE = _ALL_GLYPH_RE  # alias for clarity

# Optional f-string token constants (3.12+)
FSTART  = getattr(tokenize, "FSTRING_START", None)
FMIDDLE = getattr(tokenize, "FSTRING_MIDDLE", None)
FEND    = getattr(tokenize, "FSTRING_END", None)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _as_bytes(src: str | bytes | bytearray) -> bytes:
    return src if isinstance(src, (bytes, bytearray)) else str(src).encode("utf-8")

def _as_str(b: str | bytes | bytearray) -> str:
    return b.decode("utf-8") if isinstance(b, (bytes, bytearray)) else str(b)

def _untok_to_str(tokens) -> str:
    """
    Rebuild source safely: convert TokenInfo -> (type, string) pairs so
    tokenize.untokenize ignores start/end offsets (we change lengths).
    """
    pairs = []
    for t in tokens:
        if isinstance(t, tokenize.TokenInfo):
            pairs.append((t.type, t.string))
        else:
            pairs.append(t)
    out = tokenize.untokenize(pairs)
    return _as_str(out)

# ===== Build glyph lookup regexes =====
_glyph_all_sorted = sorted(GLYPH_TO_TOKEN.keys(), key=len, reverse=True)
_ALL_GLYPH_RE = re.compile("|".join(map(re.escape, _glyph_all_sorted))) if _glyph_all_sorted else None

def _expand_any_ops(s: str) -> str:
    """Replace OP-like glyphs (operators ∪ punctuation) with ASCII tokens within a token string."""
    for g in _OPLIKE_GLYPHS_BY_LEN:
        if g in s:
            s = s.replace(g, G2OPLIKE[g])
    return s

def _replace_all_glyphs(s: str) -> str:
    """Replace ANY code glyph (keywords, ops, punct) with its ASCII token(s)."""
    if not _ALL_GLYPH_RE:
        return s
    return _ALL_GLYPH_RE.sub(lambda m: GLYPH_TO_TOKEN[m.group(0)], s)

def _map_glyph_token(val: str):
    """
    Map a single-rune glyph to a (token_type, ascii) pair when possible.
    Only used when the ERRORTOKEN is exactly a single glyph.
    """
    if val in G2KW:
        return tokenize.NAME, G2KW[val]
    if val in G2OPLIKE:
        return tokenize.OP, G2OPLIKE[val]
    return None

# ──────────────────────────────────────────────────────────────────────────────
# Post-untokenize repairs for known artifacts
#   - f-prefix split:  NAME 'f' + STRING "'...'" -> STRING "f'...'"
#   - exponent split:  NUMBER '...e' + OP ('+'|'-') + NUMBER -> NUMBER '...e±digits'
#   - decimal split:   NUMBER '0' + OP '.' + NUMBER '98' -> NUMBER '0.98'
#   - attr split:      NAME/)/]/} + WS + '.' + NAME -> no WS around '.'
# ──────────────────────────────────────────────────────────────────────────────
_PREFIX_LETTERS = frozenset("rRbBuUfF")

def _fix_untokenize_artifacts(text: str) -> str:
    rd = io.BytesIO(_as_bytes(text)).readline
    toks = list(tokenize.tokenize(rd))
    out: list[tuple[int, str]] = []

    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        tt, ts = t.type, t.string

        # Ensure comments end the line (prevents "# ...<no NL>_WEIGHTS = {" merges)
        if tt == tokenize.COMMENT:
            out.append((tt, ts))
            nxt = toks[i + 1] if i + 1 < n else None
            if not nxt or nxt.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER):
                out.append((tokenize.NL, "\n"))
            i += 1
            continue

        # passthrough trivial structural tokens (no COMMENT here)
        if tt in (
            tokenize.ENCODING, tokenize.NL, tokenize.NEWLINE,
            tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER,
        ):
            out.append((tt, ts))
            i += 1
            continue

        # (1) Merge f/r/b/u prefixes split from the quote
        if tt == tokenize.NAME and ts and all(ch in _PREFIX_LETTERS for ch in ts):
            if i + 1 < n and toks[i + 1].type == tokenize.STRING:
                merged = ts + toks[i + 1].string
                out.append((tokenize.STRING, merged))
                i += 2
                continue

        # (2) Merge scientific exponent split: NUMBER '...e' OP [+-] NUMBER
        if tt == tokenize.NUMBER and re.fullmatch(r"[0-9_]+(?:\.[0-9_]*)?[eE]", ts or ""):
            if (
                i + 2 < n
                and toks[i + 1].type == tokenize.OP and toks[i + 1].string in {"+", "-"}
                and toks[i + 2].type == tokenize.NUMBER and re.fullmatch(r"[0-9_]+", toks[i + 2].string or "")
            ):
                merged = ts + toks[i + 1].string + toks[i + 2].string
                out.append((tokenize.NUMBER, merged))
                i += 3
                continue

        # (3) Merge decimal splits: NUMBER '.' NUMBER -> NUMBER 'X.Y'
        if tt == tokenize.NUMBER and i + 2 < n:
            t1, t2 = toks[i + 1], toks[i + 2]
            if t1.type == tokenize.OP and t1.string == "." and t2.type == tokenize.NUMBER:
                # avoid ellipsis '...'
                if not (t2.string == "." or (i + 3 < n and toks[i + 3].string == ".")):
                    merged = ts + "." + t2.string
                    out.append((tokenize.NUMBER, merged))
                    i += 3
                    continue

        # default
        out.append((tt, ts))
        i += 1

    merged = _untok_to_str(out)

    # ---- SAFE text-level fixes (no newlines; skip comment tails) ----
    def _join_attr_on_same_line(m: re.Match) -> str:
        start = m.start()
        line_start = merged.rfind("\n", 0, start) + 1
        if "#" in merged[line_start:start]:
            return m.group(0)
        return f"{m.group(1)}.{m.group(2)}"

    # Attribute join: only spaces/tabs (no '\n'); avoid comment tails
    merged = re.sub(r"(\w|\)|\]|\})[ \t]+\.(\w)", _join_attr_on_same_line, merged)
    # Decimal join fallback: only spaces/tabs (no '\n')
    merged = re.sub(r"(?<!\.)\b(\d+)[ \t]+\.(\d+)\b", r"\1.\2", merged)

    # Final canonical spacing pass
    rd2 = io.BytesIO(_as_bytes(merged)).readline
    toks2 = list(tokenize.tokenize(rd2))
    merged2 = _untok_to_str(toks2)

    return merged2

# ──────────────────────────────────────────────────────────────────────────────
# Compression (Python -> glyph tokens)
# ──────────────────────────────────────────────────────────────────────────────

def _compress_tokens(tokens: Iterable[tokenize.TokenInfo]) -> Iterable[tokenize.TokenInfo]:
    fdepth = 0
    for t in tokens:
        typ, val, start, end, line = t.type, t.string, t.start, t.end, t.line

        # Hard rule: comments always terminate the physical line
        if typ == tokenize.COMMENT:
            yield t
            yield tokenize.TokenInfo(tokenize.NL, "\n", start, end, line)
            continue

        # Never rewrite inside f-strings
        if FSTART is not None and typ == FSTART:
            fdepth += 1; yield t; continue
        if FEND is not None and typ == FEND:
            fdepth = max(0, fdepth - 1); yield t; continue
        if fdepth > 0 or (FMIDDLE is not None and typ == FMIDDLE):
            yield t; continue

        # Keywords -> glyphs
        if typ == tokenize.NAME and val in _PY_KEYWORDS:
            yield tokenize.TokenInfo(typ, KW_MAP[val], start, end, line); continue

        # Operators/punct -> glyphs, but DO NOT map curly braces on compress
        if typ == tokenize.OP:
            if val in {"{", "}"}:
                yield t; continue
            if val in _OP_TOKENS:
                yield tokenize.TokenInfo(typ, OPLIKE_FORWARD[val], start, end, line); continue

        # Default passthrough
        yield t

# ──────────────────────────────────────────────────────────────────────────────
# Expansion (glyph tokens -> Python)
# ──────────────────────────────────────────────────────────────────────────────

def _expand_tokens(tokens: Iterable[tokenize.TokenInfo]) -> Iterable[tokenize.TokenInfo]:
    fdepth = 0
    for t in tokens:
        typ, val, start, end, line = t.type, t.string, t.start, t.end, t.line

        # Hard rule: comments always terminate the physical line.
        # Ensures any following brace starts on a new line (prevents '{' being
        # swallowed by a trailing comment).
        if typ == tokenize.COMMENT:
            yield t
            yield tokenize.TokenInfo(tokenize.NL, "\n", start, end, line)
            continue

        # Preserve f-string regions verbatim
        if FSTART is not None and typ == FSTART:
            fdepth += 1; yield t; continue
        if FEND is not None and typ == FEND:
            fdepth = max(0, fdepth - 1); yield t; continue
        if fdepth > 0 or (FMIDDLE is not None and typ == FMIDDLE):
            yield t; continue

        # Never touch literal bodies
        if typ == tokenize.STRING:
            yield t; continue

        # Keyword glyph came through as NAME
        if typ == tokenize.NAME and val in G2KW:
            yield tokenize.TokenInfo(tokenize.NAME, G2KW[val], start, end, line); continue

        if typ == tokenize.OP:
            # Keyword glyphs sometimes get tokenized as OP (⮐ 'return', ⧁ 'if', ...)
            if val in G2KW:
                yield tokenize.TokenInfo(tokenize.NAME, G2KW[val], start, end, line); continue
            # Otherwise normalize OP-like glyphs only
            norm = _expand_any_ops(val)
            yield tokenize.TokenInfo(tokenize.OP, norm, start, end, line); continue

        if typ == tokenize.ERRORTOKEN:
            # Single glyph? Map directly to NAME/OP
            mapped = _map_glyph_token(val)
            if mapped:
                new_typ, new_val = mapped
                yield tokenize.TokenInfo(new_typ, new_val, start, end, line); continue
            # Mixed or adjacent glyphs: replace ALL code glyphs (keywords + ops + punct)
            norm = _replace_all_glyphs(val)
            yield tokenize.TokenInfo(tokenize.ERRORTOKEN, norm, start, end, line); continue

        # Safety net: if anything else still contains code glyphs, replace all
        if _CODE_GLYPH_RE and _CODE_GLYPH_RE.search(val):
            norm = _replace_all_glyphs(val)
            yield tokenize.TokenInfo(typ, norm, start, end, line); continue

        yield t

# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def _as_text(x: str | bytes) -> str:
    return x.decode("utf-8", errors="replace") if isinstance(x, (bytes, bytearray)) else str(x)

def compress_text_py(py_src: str | bytes) -> str:
    """
    Python → Photon (token-based).
    NOTE: Do NOT re-tokenize the glyph output (no _fix_untokenize_artifacts here),
    because glyphs remove real braces and the tokenizer loses bracket context.
    """
    raw_text = _as_text(py_src)
    buf = io.BytesIO(raw_text.encode("utf-8"))
    toks = list(tokenize.tokenize(buf.readline))
    out  = list(_compress_tokens(toks))
    s = _untok_to_str(out)
    return s  # no post-fix pass here

def expand_text_py(src: str | bytes) -> str:
    """
    Photon → Python (token-based).
    After glyphs are mapped back to real Python tokens, it's safe to tidy
    common untokenize artifacts.
    """
    raw_text = _as_text(src)
    buf = io.BytesIO(raw_text.encode("utf-8"))
    toks = list(tokenize.tokenize(buf.readline))
    out  = list(_expand_tokens(toks))
    s = _untok_to_str(out)
    s = _fix_untokenize_artifacts(s)  # safe now (real braces/parens restored)
    return s

def contains_code_glyphs(text: str) -> bool:
    return bool(_CODE_GLYPH_RE and _CODE_GLYPH_RE.search(text))

__all__ = [
    "compress_text_py", "expand_text_py", "contains_code_glyphs",
    "TOKEN_TO_GLYPH", "GLYPH_TO_TOKEN",
]