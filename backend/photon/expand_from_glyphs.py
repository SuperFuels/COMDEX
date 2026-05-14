"""
Reverse expansion: reconstruct human-readable symbolic text
from glyph stream + resonance + canonical operator metadata.

Priority:
1) Operator metadata bridge (human label)
2) Canonical ops namespaced key
3) Resonance-weighted contextual choice
4) Literal glyph fallback

Example:
    [{"text":"Ω"}, {"text":"⊕"}, {"text":"A"}]
->  "Omega superpose A"
"""

from typing import List, Dict, Any
from functools import lru_cache

# ───────── Canonical Photon/Symatics metadata ─────────

try:
    from backend.codexcore_virtual.instruction_metadata_bridge import OPERATOR_METADATA
except Exception:
    OPERATOR_METADATA = {}

try:
    from backend.modules.codex.canonical_ops import CANONICAL_OPS
except Exception:
    CANONICAL_OPS = {}

# ───────── Resonance + util ─────────

from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.patterns.pattern_registry import stringify_glyph

rmc = ResonantMemoryCache()

# ───────── Fallback micro-lexicon (rare) ─────────
# only used when NOT in metadata AND no resonance clue
try:
    from backend.modules.glyphos.glyph_lexicon import GLYPH_LEXICON
except Exception:
    GLYPH_LEXICON = {}


# ========== RESOLUTION ENGINE ==========

@lru_cache(maxsize=4096)
def resolve_candidate(glyph_txt: str) -> str:
    """
    Resolve glyph -> natural language token via:
    - canonical operator metadata (primary)
    - canonical ops namespace (secondary)
    - resonance weighted choice (if ambiguous)
    - lexicon fallback
    - literal fallback
    """

    # 1) Canonical operator metadata (gold source)
    meta = OPERATOR_METADATA.get(glyph_txt)
    if meta and isinstance(meta, dict) and "name" in meta:
        return meta["name"].replace("_", " ")

    # 2) Canonical ops namespace -> strip domain prefix to readable form
    if glyph_txt in CANONICAL_OPS:
        namespaced = CANONICAL_OPS[glyph_txt]
        # e.g. "quantum:⊕" -> "quantum superpose"
        if ":" in namespaced:
            domain, sym = namespaced.split(":", 1)
            # map domain back to english and symbol to readable
            return domain.replace("_"," ") + " " + sym

    # 3) Lexicon fallback set
    base = GLYPH_LEXICON.get(glyph_txt)
    if not base:
        return glyph_txt  # literal

    if isinstance(base, str):
        return base

    if isinstance(base, list) and len(base) == 1:
        return base[0]

    # 4) Multi-mapping -> resonance score choice
    best = None
    best_score = -1.0

    for candidate in base:
        entry = rmc.recall(candidate.lower())
        score = 0.0

        if entry and isinstance(entry, dict):
            score = (
                entry.get("stability", 0.0)
                + entry.get("coherence", 0.0)
                + entry.get("SQI_avg", 0.0)
            )

        if score > best_score:
            best_score = score
            best = candidate

    return best or base[0]


def expand_glyph(g: Dict[str, Any]) -> str:
    txt = g.get("text") or stringify_glyph(g)
    return resolve_candidate(txt)


def expand_from_glyphs(glyphs: List[Dict[str, Any]]) -> str:
    words = [expand_glyph(g) for g in glyphs]
    out = " ".join(words)
    return out.replace("  ", " ").strip()


# ========== CLI ==========

if __name__ == "__main__":
    import sys, json

    if sys.stdin.isatty():
        print("Usage: cat glyphs.json | PYTHONPATH=. python backend/photon/expand_from_glyphs.py")
        sys.exit(0)

    raw = json.load(sys.stdin)
    print(expand_from_glyphs(raw))