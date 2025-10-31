# backend/modules/glyphos/constants.py
# 🔒 Single source of truth for glyph alphabet + defaults

from __future__ import annotations

from pathlib import Path
import json
import unicodedata as _ud

# --- Raw frozen alphabet (edit here only) ---
# NOTE: Use "⚛" (no variation selector). The sanitizer below will strip any
# stray non-spacing/format marks just in case.
GLYPH_ALPHABET_RAW = (
    "⚛☯☀☾☽✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿❀❁❂❃❄❅❆❇❈❉❊❋"
    "⊕↔∇⟲μπΦΨΩΣΔΛΘΞΓαβγδλστωηικ"
    "◇◆◧◨◩◪◫⬡⬢⬣⬤⟁⧖"
)

def _sanitize(alpha: str) -> str:
    """Keep only Letters/Symbols; drop marks/format (e.g., variation selectors)."""
    keep = []
    for ch in alpha:
        cat = _ud.category(ch)
        if cat[0] in ("L", "S"):  # Letter or Symbol
            keep.append(ch)
    return "".join(keep)

# Public export used everywhere
GLYPH_ALPHABET: str = _sanitize(GLYPH_ALPHABET_RAW)

# Default/fallback glyph used when no specific mapping is found
DEFAULT_GLYPH = "✦"

# --- Build RESERVED_GLYPHS from maps (ops + code tokens) + Greek + default ---
_BASE = Path(__file__).resolve().parents[1]  # .../backend/modules
_PH_MAP = _BASE / "photonlang" / "photon_reserved_map.json"
_PY_TOKEN_MAP = _BASE / "photonlang" / "python_token_map.json"  # keywords/operators/punct → glyphs

# Greek block (upper + lower)
_GREEK_UPPER = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
_GREEK_LOWER = "αβγδεζηθικλμνξοπρστυφχψω"
_GREEK_SET   = set(_GREEK_UPPER + _GREEK_LOWER)

def _load_reserved_from_json() -> set[str]:
    """
    Load reserved operator glyphs/tokens from photon_reserved_map.json.
    Splits multi-rune tokens like 'μπ' into {'μ','π'} so the generator never
    emits them as word glyphs.
    """
    try:
        data = json.loads(_PH_MAP.read_text(encoding="utf-8"))
        op_chars: set[str] = set()

        # Operators across domains
        for arr in (data.get("ops") or {}).values():
            for token in (arr or []):
                op_chars.update(token)  # split multi-rune tokens

        # Also reserve conceptual glyphs listed under "glyphs"
        for g in (data.get("glyphs") or []):
            op_chars.update(g)

        return op_chars
    except Exception:
        # Safe minimal fallback if JSON is missing / malformed
        return set("⊕↔∇⟲μπ→⇒⧖≈ΦΨΩΣΔΛΘΞΓ")

def _load_code_glyphs() -> set[str]:
    """
    Load code-only glyphs from python_token_map.json (keywords/operators/punct).
    Any glyph used for code tokens is reserved for *code*, not for word glyphs.
    """
    try:
        data = json.loads(_PY_TOKEN_MAP.read_text(encoding="utf-8"))
        vals: set[str] = set()
        for section in ("keywords", "operators", "punct", "punctuation"):  # be tolerant
            mapping = data.get(section) or {}
            for glyph in mapping.values():
                # split multi-rune mappings, reserve per-rune
                for ch in glyph:
                    vals.add(ch)
        return vals
    except Exception:
        # Optional file; if absent, just reserve nothing from it
        return set()

# 🔐 Single source of truth for “do not use for words”
RESERVED_GLYPHS: set[str] = (
    _load_reserved_from_json()   # ops/glyphs from photon_reserved_map.json
    | _load_code_glyphs()        # code token glyphs from python_token_map.json
    | _GREEK_SET                 # all Greek letters (upper/lower)
    | {DEFAULT_GLYPH}            # default fallback glyph is not assignable to words
)

def filtered_alphabet() -> str:
    """Alphabet stripped of reserved runes (use for unique-word generators)."""
    return "".join(ch for ch in GLYPH_ALPHABET if ch not in RESERVED_GLYPHS)

__all__ = [
    "GLYPH_ALPHABET",
    "GLYPH_ALPHABET_RAW",
    "DEFAULT_GLYPH",
    "RESERVED_GLYPHS",
    "filtered_alphabet",
]