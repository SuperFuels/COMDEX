# File: backend/modules/glyphos/glyph_utils.py

import hashlib
from typing import List


def parse_to_glyphos(data: str) -> List[str]:
    """Parse natural language into symbolic glyphs based on keyword matching."""
    text = data.lower()
    glyphs = []

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

    if not glyphs:
        glyphs.append("✦")  # Default: Milestone

    return glyphs


def summarize_to_glyph(summary_text: str) -> str:
    """Return the most representative glyph from a summary text string."""
    glyphs = parse_to_glyphos(summary_text)
    return glyphs[0] if glyphs else "✦"


def generate_hash(glyphs: List[str]) -> str:
    """
    Generate a unique hash string for a list of glyphs, used for deduplication.
    Ensures consistent symbolic packet recognition.
    """
    raw = "|".join(sorted(glyphs))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()