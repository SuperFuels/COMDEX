# File: backend/modules/glyphos/glyph_utils.py

import hashlib, json
from typing import List, Optional, Tuple

# 🔒 Freeze glyph set + defaults from a single source of truth
from backend.modules.glyphos.constants import GLYPH_ALPHABET, DEFAULT_GLYPH

# ─────────────────────────────────────────────
# ✅ Base natural-language -> glyph mapping (existing behavior)
# ─────────────────────────────────────────────

def parse_to_glyphos(data: str) -> List[str]:
    """Parse natural language into symbolic glyphs based on keyword matching."""
    text = (data or "").lower()
    glyphs: List[str] = []

    if any(word in text for word in ["milestone", "achievement", "goal reached"]):
        glyphs.append("✦")  # Milestone

    if any(word in text for word in ["dream", "imagine", "vision"]):
        glyphs.append("🛌")  # Dream

    if any(word in text for word in ["mutate", "change", "evolve"]):
        glyphs.append("⬁")  # Mutation

    if any(word in text for word in ["memory", "remember", "recall"]):
        glyphs.append("🧠")  # Memory

    if any(word in text for word in ["navigate", "map", "path", "journey"]):
        glyphs.append("🧭")  # Navigation

    # Default if no meaning detected
    if not glyphs:
        glyphs.append(DEFAULT_GLYPH)

    return glyphs


def summarize_to_glyph(summary_text: str) -> str:
    """Return the most representative glyph from a summary text string."""
    glyphs = parse_to_glyphos(summary_text)
    return glyphs[0] if glyphs else DEFAULT_GLYPH


def generate_hash(glyphs: List[str]) -> str:
    """
    Generate a unique hash string for a list of glyphs.
    Ensures consistent symbolic packet recognition.
    """
    raw = "|".join(sorted(glyphs))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_valid_glyph(symbol: str) -> bool:
    """Check if a symbol is in the frozen GLYPH_ALPHABET (fast set lookup)."""
    # Cache the set once at import time
    return symbol in _ALPHABET_SET

_ALPHABET_SET = set(GLYPH_ALPHABET)

# ─────────────────────────────────────────────
# ✅ Document Format Header Glyph Layer
# ─────────────────────────────────────────────

# Format -> Glyph
FORMAT_GLYPHS = {
    "json": "◧",
    "yaml": "◨",
    "xml": "⌘",
    "html": "⌘",
    "md": "✎",
    "markdown": "✎",
    "code": "⚙",
    "python": "🐍",
    "log": "⋄",
    "photon": "⚡",
    "text": "□",
}

# Inverse map
GLYPH_FORMATS = {v: k for k, v in FORMAT_GLYPHS.items()}


def _filename_hint_to_format(filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    f = filename.lower()

    if f.endswith(".json"): return "json"
    if f.endswith((".yml", ".yaml")): return "yaml"
    if f.endswith(".xml"): return "xml"
    if f.endswith((".html", ".htm")): return "html"
    if f.endswith((".md", ".markdown")): return "md"
    if f.endswith((".log", ".logs")): return "log"
    if f.endswith((".photo", ".ptn")): return "photon"
    if f.endswith(".py"): return "python"

    return None


def detect_doc_format(text: str, *, filename: Optional[str]=None, fmt_hint: Optional[str]=None) -> Tuple[str, str]:
    """
    Decide document format glyph (JSON / YAML / code / log etc.)
    Priority:
      1) explicit fmt_hint
      2) filename extension
      3) content sniff
    """
    # 1) explicit override
    if fmt_hint in FORMAT_GLYPHS:
        return fmt_hint, FORMAT_GLYPHS[fmt_hint]

    # 2) filename
    by_file = _filename_hint_to_format(filename)
    if by_file:
        return by_file, FORMAT_GLYPHS[by_file]

    # 3) content sniff
    s = (text or "").lstrip()

    if s.startswith("{") or s.startswith("["):
        return "json", FORMAT_GLYPHS["json"]
    if s.startswith("<") or "<?xml" in s[:20]:
        return "xml", FORMAT_GLYPHS["xml"]
    if s.startswith(("# ", "## ", "### ")):
        return "md", FORMAT_GLYPHS["md"]
    if any(x in s[:100] for x in ("INFO:", "WARN", "ERROR", "[")) and ":" in s[:40]:
        return "log", FORMAT_GLYPHS["log"]

    return "text", FORMAT_GLYPHS["text"]


# ─────────────────────────────────────────────
# ✅ Reverse expansion scaffold (v0.1)
# ─────────────────────────────────────────────

def expand_from_glyphs(glyphs: List[str]) -> str:
    """
    Experimental reversible pipeline stub.
    Reads format header and expands to placeholder text for now.
    """
    if not glyphs:
        return ""

    head = glyphs[0]
    fmt = GLYPH_FORMATS.get(head, "text")
    body = glyphs[1:]

    if fmt == "json":
        return '{"_reconstructed": ' + json.dumps(body, ensure_ascii=False) + "}"
    if fmt in ("xml", "html"):
        return "<reconstructed>" + " ".join(body) + "</reconstructed>"
    if fmt == "md":
        return "# Reconstructed\n\n" + " ".join(body) + "\n"
    if fmt == "python":
        return "# reconstructed.py\n" + " ".join(body) + "\n"
    if fmt == "photon":
        return "/* photon capsule */\n" + " ".join(body) + "\n"
    if fmt == "log":
        return " | ".join(body) + "\n"

    return " ".join(body)