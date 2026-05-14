"""
instruction_metadata_bridge.py
Canonical operator registry bridging CodexCore, GlyphOS, and Symatics.
All operator definitions should live here, tagged by domain.
"""

from typing import Dict, Optional, List

# ─── Master Operator Metadata ───────────────────────────────────────────────────

OPERATOR_METADATA: Dict[str, Dict] = {

    # ─── Logic ────────────────────────────
    "∧": {"name": "and", "domain": "logic", "type": "operator", "tags": ["boolean", "conjunction"]},
    "∨": {"name": "or", "domain": "logic", "type": "operator", "tags": ["boolean", "disjunction"]},
    "¬": {"name": "not", "domain": "logic", "type": "operator", "tags": ["boolean", "negation"]},
    "->": {"name": "implies", "domain": "logic", "type": "operator", "tags": ["flow", "conditional"]},
    "↔": {"name": "equivalence", "domain": "logic", "type": "relation", "tags": ["compare", "biconditional"]},
    "⊕": {"name": "xor", "domain": "logic", "type": "operator", "tags": ["boolean", "exclusive"]},
    "⊗": {"name": "tensor_logic", "domain": "logic", "type": "operator", "tags": ["structure", "product"]},

    # ─── Quantum ──────────────────────────
    "⊕_q": {"name": "quantum_superpose", "domain": "quantum", "type": "operator", "tags": ["superposition", "merge"]},
    "⊗_q": {"name": "quantum_tensor", "domain": "quantum", "type": "operator", "tags": ["tensor", "composition"]},
    "μ": {"name": "measure", "domain": "quantum", "type": "operator", "tags": ["collapse", "observation"]},
    "π": {"name": "project", "domain": "quantum", "type": "operator", "tags": ["projection", "state_space"]},
    "⧜": {"name": "superposition", "domain": "quantum", "type": "operator", "tags": ["state", "coherence"]},
    "⧝": {"name": "collapse", "domain": "quantum", "type": "operator", "tags": ["measurement", "reduction"]},
    "⧠": {"name": "quantum_box", "domain": "quantum", "type": "operator", "tags": ["projection", "collapse"]},
    "↔_q": {"name": "entangle", "domain": "quantum", "type": "relation", "tags": ["link", "correlation"]},
    "ψ⟩": {"name": "ket", "domain": "quantum", "type": "state", "tags": ["wavefunction", "vector"]},
    "⟨ψ|": {"name": "bra", "domain": "quantum", "type": "state", "tags": ["dual", "vector"]},
    "Â": {"name": "observable", "domain": "quantum", "type": "operator", "tags": ["measurement", "operator"]},
    "H": {"name": "hadamard", "domain": "quantum", "type": "gate", "tags": ["superposition", "transform"]},
    "[": {"name": "commutator_open", "domain": "quantum", "type": "syntax", "tags": ["delimiter"]},
    "]": {"name": "commutator_close", "domain": "quantum", "type": "syntax", "tags": ["delimiter"]},
    "∇": {"name": "gradient", "domain": "quantum", "type": "operator", "tags": ["differential", "field"]},

    # ─── Symatics / Physics ───────────────
    "⊕_s": {"name": "superpose_wave", "domain": "symatics", "type": "operator", "tags": ["merge", "constructive"]},
    "⊖": {"name": "invert_wave", "domain": "symatics", "type": "operator", "tags": ["destructive", "phase_inversion"]},
    "⊗_s": {"name": "tensor_bind", "domain": "symatics", "type": "operator", "tags": ["bind", "tensor"]},
    "⋈": {"name": "phase_join", "domain": "symatics", "type": "operator", "tags": ["interference", "phase"]},
    "⟲": {"name": "reflect", "domain": "symatics", "type": "operator", "tags": ["loop", "mutation", "resonance"]},
    "↺": {"name": "recursion", "domain": "symatics", "type": "operator", "tags": ["feedback", "reflection"]},
    "cancel": {"name": "cancel", "domain": "symatics", "type": "keyword", "tags": ["reduction", "filter"]},
    "damping": {"name": "damping", "domain": "symatics", "type": "keyword", "tags": ["attenuation", "decay"]},
    "resonance": {"name": "resonance", "domain": "symatics", "type": "keyword", "tags": ["oscillation", "coherence"]},
    "⟁": {"name": "dimension_lock", "domain": "symatics", "type": "barrier", "tags": ["constraint", "gate"]},
    "⌬": {"name": "compression_lens", "domain": "symatics", "type": "modifier", "tags": ["reduce", "optimize"]},
    "≈": {"name": "similarity", "domain": "physics", "type": "operator", "tags": ["wave", "coherence"]},
    "≈_p": {"name": "physical_similarity", "domain": "physics", "type": "operator", "tags": ["wave", "equivalence", "coherence"]},
    "⊗_p": {"name": "physical_tensor", "domain": "physics", "type": "operator", "tags": ["tensor", "field", "composition"]},

    # ─── Photon ───────────────────────────
    "⊙": {"name": "photon_emission", "domain": "photon", "type": "operator", "tags": ["emit", "absorb"]},
    "~": {"name": "photon_equivalence", "domain": "photon", "type": "relation", "tags": ["similarity", "coherence"]},
    "photon": {"name": "photon", "domain": "photon", "type": "primitive", "tags": ["quantum_light", "elemental"]},
    "wave": {"name": "wave", "domain": "photon", "type": "primitive", "tags": ["propagation", "field"]},

    # ─── Control / Flow ───────────────────
    "⧖": {"name": "delay", "domain": "control", "type": "operator", "tags": ["time", "defer"]},
    "->_c": {"name": "trigger", "domain": "control", "type": "operator", "tags": ["execution", "flow"]},
    "⟲_c": {"name": "update_loop", "domain": "control", "type": "operator", "tags": ["recursion", "mutation"]},

    # ─── GlyphOS Unique ───────────────────
    "🜁": {"name": "memory_seed", "domain": "glyph", "type": "instruction", "tags": ["init", "load"]},
    "⚛": {"name": "ethic_filter", "domain": "glyph", "type": "modifier", "tags": ["soul_law"]},
    "✦": {"name": "dream_trigger", "domain": "glyph", "type": "event", "tags": ["reflection", "vision"]},
    "🧭": {"name": "navigation_pulse", "domain": "glyph", "type": "action", "tags": ["teleport", "wormhole"]},
}

# ─── Derived Reverse Index ──────────────────────────────────────────────────────

DOMAIN_INDEX: Dict[str, List[str]] = {}
for sym, meta in OPERATOR_METADATA.items():
    domain = meta.get("domain", "unknown")
    DOMAIN_INDEX.setdefault(domain, []).append(sym)

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


def list_by_domain(domain: str) -> List[str]:
    """
    List all symbols registered under a given domain (e.g., 'logic', 'quantum').
    """
    return DOMAIN_INDEX.get(domain, [])


def list_all_domains() -> List[str]:
    """
    Return all known domains in the operator registry.
    """
    return sorted(DOMAIN_INDEX.keys())