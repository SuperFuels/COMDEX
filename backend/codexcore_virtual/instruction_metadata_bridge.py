"""
instruction_metadata_bridge.py
Canonical operator registry bridging CodexCore, GlyphOS, and Symatics.
All operator definitions should live here, tagged by domain.
"""

from typing import Dict, Optional

# ─── Master Operator Metadata ───────────────────────────────────────────────────

OPERATOR_METADATA: Dict[str, Dict] = {
    # ─── Logic ────────────────────────────
    "∧": {"name": "and", "domain": "logic", "type": "operator", "tags": ["boolean"]},
    "∨": {"name": "or", "domain": "logic", "type": "operator", "tags": ["boolean"]},
    "¬": {"name": "not", "domain": "logic", "type": "operator", "tags": ["boolean"]},
    "→": {"name": "implies", "domain": "logic", "type": "operator", "tags": ["flow"]},
    "≐": {"name": "equivalence", "domain": "logic", "type": "relation", "tags": ["compare"]},

    # ─── Symbolic / Codex ─────────────────
    "⊕": {"name": "superpose", "domain": "symbolic", "type": "operator", "tags": ["merge"]},
    "⟲": {"name": "reflect", "domain": "symbolic", "type": "operator", "tags": ["mutation", "loop"]},
    "↔": {"name": "entangle", "domain": "symbolic", "type": "operator", "tags": ["link"]},
    "⧖": {"name": "delay", "domain": "symbolic", "type": "operator", "tags": ["time"]},

    # ─── Quantum ──────────────────────────
    "⧜": {"name": "superposition", "domain": "quantum", "type": "operator", "tags": ["state"]},
    "⧝": {"name": "measure", "domain": "quantum", "type": "operator", "tags": ["collapse"]},
    "⧠": {"name": "project", "domain": "quantum", "type": "operator", "tags": ["projection"]},
    "⊗": {"name": "tensor_product", "domain": "quantum", "type": "operator", "tags": ["algebra"]},
    "∇": {"name": "gradient", "domain": "quantum", "type": "operator", "tags": ["differential"]},

    # ─── Physics / Symatics ───────────────
    "≈": {"name": "similarity", "domain": "physics", "type": "operator", "tags": ["wave"]},
    "cancel": {"name": "cancel", "domain": "physics", "type": "keyword", "tags": ["reduction"]},
    "damping": {"name": "damping", "domain": "physics", "type": "keyword", "tags": ["attenuation"]},
    "resonance": {"name": "resonance", "domain": "physics", "type": "keyword", "tags": ["oscillation"]},
    "photon": {"name": "photon", "domain": "physics", "type": "keyword", "tags": ["primitive"]},
    "wave": {"name": "wave", "domain": "physics", "type": "keyword", "tags": ["primitive"]},

    # ─── GlyphOS Unique ───────────────────
    "🜁": {"name": "memory_seed", "domain": "glyph", "type": "instruction", "tags": ["init", "load"]},
    "⚛": {"name": "ethic_filter", "domain": "glyph", "type": "modifier", "tags": ["soul_law"]},
    "✦": {"name": "dream_trigger", "domain": "glyph", "type": "event", "tags": ["reflection"]},
    "🧭": {"name": "navigation_pulse", "domain": "glyph", "type": "action", "tags": ["teleport", "wormhole"]},
    "⌬": {"name": "compression_lens", "domain": "glyph", "type": "modifier", "tags": ["reduce", "optimize"]},
    "⟁": {"name": "dimension_lock", "domain": "glyph", "type": "barrier", "tags": ["test", "gate"]},
}

# ─── API ────────────────────────────────────────────────────────────────────────

def get_instruction_metadata(symbol: str) -> Optional[Dict]:
    """
    Lookup metadata for a symbol/operator.
    Returns dict with name, domain, type, tags, or None if not found.
    """
    return OPERATOR_METADATA.get(symbol)


def list_all_symbols() -> Dict[str, Dict]:
    """
    Return the full operator registry.
    """
    return OPERATOR_METADATA