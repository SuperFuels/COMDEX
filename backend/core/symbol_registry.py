# ============================================
# 📁 backend/modules/core/symbol_registry.py
# ============================================
"""
Central Symbol Registry (Locked Sets + Photon Extensions)
"""

from typing import Dict, Any

# -------------------------------
# CodexLang (LOCKED)
# -------------------------------
CODEX_SYMBOLS: Dict[str, str] = {
    "∀": "for_all (universal quantifier)",
    "∃": "exists (existential quantifier)",
    "¬": "not (logical negation)",
    "→": "implies",
    "↔": "iff (if and only if)",
    "∧": "and",
    "∨": "or",
    "⊕": "xor",
    "↑": "nand",
    "↓": "nor",
    "=": "equals"
}

# -------------------------------
# GlyphOS (LOCKED)
# -------------------------------
GLYPH_OS_SYMBOLS: Dict[str, str] = {
    "symbol": "glyph node symbol",
    "value": "assigned value",
    "action": "operation/action binding",
    "coord": "tree coordinate (debug/trace)"
}

# -------------------------------
# Symatics (LOCKED)
# -------------------------------
SYMATIC_SYMBOLS: Dict[str, str] = {
    "⊕": "resonance superposition (combine)",
    "⊗": "fusion / reinforcement",
    "⊖": "cancellation (destructive interference)",
    "∇": "collapse (resonant state → form)",
    "★": "quality projection (SQI weighting)",
    "☄": "broadcast resonance"
}

# -------------------------------
# Photon Algebra (EXTEND AROUND LOCKS)
# -------------------------------
PHOTON_SYMBOLS: Dict[str, str] = {
    # ✅ aligned with Symatics (no conflict)
    "⊕": "superpose (combine, consistent with symatics)",
    "⊗": "fuse (consistent with symatics)",
    "⊖": "cancel (consistent with symatics)",
    "∇": "collapse (consistent with symatics)",
    "★": "score/measure (consistent with symatics)",

    # ✅ aligned with CodexLang
    "¬": "negate (phase inversion, consistent with codex)",
    
    # ⚠ conflict with CodexLang: ↔
    # In CodexLang: iff
    # In Photon: entangle
    # → Keep Photon '↔' but alias an alternate (e.g. '∞' or custom glyph)
    "↔": "entangle (photon semantics — shadowed by CodexLang iff)",
    "∞": "alias for entangle (photon-safe symbol)",

    # Photon-unique
    "☄": "broadcast (photon resonance propagation)",
    "λ": "drift / wavelength phase shift",
    "Ψ": "state (wavefunction glyph)",
}

# -------------------------------
# Registry
# -------------------------------
REGISTRY: Dict[str, Dict[str, Any]] = {
    "codex": CODEX_SYMBOLS,
    "glyph_os": GLYPH_OS_SYMBOLS,
    "symatics": SYMATIC_SYMBOLS,
    "photon": PHOTON_SYMBOLS,
}


def lookup_symbol(symbol: str) -> Dict[str, str]:
    """
    Lookup a symbol across all registries.
    Returns dict: {domain: meaning}
    """
    result = {}
    for domain, table in REGISTRY.items():
        if symbol in table:
            result[domain] = table[symbol]
    return result


if __name__ == "__main__":
    # Debug harness: check overlaps
    for sym in set().union(*[set(tbl.keys()) for tbl in REGISTRY.values()]):
        defs = lookup_symbol(sym)
        if len(defs) > 1:
            print(f"⚠ Overlap for {sym}: {defs}")