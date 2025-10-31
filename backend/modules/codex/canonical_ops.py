# backend/modules/codex/canonical_ops.py

# ────────────────────────────────────────────────
# Canonical operator mapping
# Unified registry across Logic, Quantum, Symatics, Photon, Physics
# Each symbol maps to a canonical namespaced identifier.
# ────────────────────────────────────────────────

CANONICAL_OPS = {
    # ─── Logic ────────────────────────────
    "⊕": "logic:⊕",
    "⊗": "logic:⊗",
    "∧": "logic:∧",
    "∨": "logic:∨",
    "¬": "logic:¬",
    "→": "logic:→",
    "↔": "logic:↔",

    # ─── Quantum ─────────────────────────
    # ⚠️ “↔” remains in COLLISIONS for dual meaning
    "⊕_q": "quantum:⊕",
    "⊗_q": "quantum:⊗",
    "μ": "quantum:μ",
    "π": "quantum:π",
    "⧜": "quantum:⧜",
    "⧝": "quantum:⧝",
    "⧠": "quantum:⧠",
    "ψ⟩": "quantum:ket",
    "⟨ψ|": "quantum:bra",
    "Â": "quantum:A",
    "H": "quantum:H",
    "[": "quantum:commutator_open",
    "]": "quantum:commutator_close",

    # ─── Symatics ────────────────────────
    "⊕_s": "symatics:⊕",
    "⊗_s": "symatics:⊗",
    "⊖": "symatics:⊖",
    "⋈": "symatics:⋈",
    "⟲": "symatics:⟲",
    "↺": "symatics:↺",
    "cancel": "symatics:cancel",
    "damping": "symatics:damping",
    "resonance": "symatics:resonance",
    "⟁": "symatics:⟁",
    "⌬": "symatics:⌬",

    # ─── Math / Physics ─────────────────
    "∇": "math:∇",
    "⊗_p": "physics:⊗",
    "≈": "physics:≈",

    # ─── Control / Flow ─────────────────
    "⧖": "control:⧖",
    "→_c": "control:→",
    "⟲_c": "control:⟲",

    # ─── Photon ─────────────────────────
    "⊙": "photon:⊙",
    "≈_p": "photon:≈",
    "~": "photon:≈",
    "photon": "photon:primitive",
    "wave": "photon:wave",
}

# ────────────────────────────────────────────────
# Collisions table (ambiguous ops only)
# Some operators occur in multiple namespaces.
# ────────────────────────────────────────────────

COLLISIONS = {
    "⊗": ["logic:⊗", "physics:⊗", "symatics:⊗", "quantum:⊗"],
    "⊕": ["logic:⊕", "quantum:⊕", "symatics:⊕"],
    "↔": ["logic:↔", "quantum:↔"],
    "≈": ["photon:≈", "physics:≈"],
}

# ────────────────────────────────────────────────
# Operator metadata
# Explicit symbol registry for consistency and traceability
# ────────────────────────────────────────────────

OP_METADATA = {
    # ─── Logic ───────────────────────────
    "logic:⊕": {
        "description": "Logical XOR / exclusive disjunction",
        "symbols": ["⊕"],
    },
    "logic:⊗": {
        "description": "Logical product (structural conjunction)",
        "symbols": ["⊗"],
    },
    "logic:¬": {
        "description": "Logical negation / NOT operator",
        "symbols": ["¬"],
    },
    "logic:∨": {
        "description": "Logical OR / disjunction",
        "symbols": ["∨"],
    },
    "logic:∧": {
        "description": "Logical AND / conjunction",
        "symbols": ["∧"],
    },
    "logic:→": {
        "description": "Logical implication",
        "symbols": ["→"],
    },
    "logic:↔": {
        "description": "Logical equivalence (biconditional)",
        "symbols": ["↔"],
    },

    # ─── Quantum ─────────────────────────
    "quantum:⊕": {
        "description": "Quantum XOR-like operation (superposition)",
        "symbols": ["⊕_q"],
    },
    "quantum:⊗": {
        "description": "Quantum tensor product (state composition)",
        "symbols": ["⊗_q"],
    },
    "quantum:μ": {
        "description": "Measurement operator (collapse trigger)",
        "symbols": ["μ"],
    },
    "quantum:π": {
        "description": "Projection operator (state projection)",
        "symbols": ["π"],
    },
    "quantum:⧜": {
        "description": "Quantum superposition state operator",
        "symbols": ["⧜"],
    },
    "quantum:⧝": {
        "description": "Quantum collapse operator",
        "symbols": ["⧝"],
    },
    "quantum:⧠": {
        "description": "Quantum projection box / normalization operator",
        "symbols": ["⧠"],
    },
    "quantum:↔": {
        "description": "Quantum entanglement equivalence relation",
        "symbols": ["↔"],
    },
    "quantum:A": {
        "description": "Quantum observable operator Â",
        "symbols": ["Â"],
    },
    "quantum:H": {
        "description": "Hadamard gate / uniform superposition",
        "symbols": ["H"],
    },
    "quantum:ket": {
        "description": "Quantum ket state |ψ⟩",
        "symbols": ["ψ⟩"],
    },
    "quantum:bra": {
        "description": "Quantum bra state ⟨ψ|",
        "symbols": ["⟨ψ|"],
    },
    "quantum:commutator_open": {
        "description": "Commutator opening bracket",
        "symbols": ["["],
    },
    "quantum:commutator_close": {
        "description": "Commutator closing bracket",
        "symbols": ["]"],
    },

    # ─── Symatics ────────────────────────
    "symatics:⊕": {
        "description": "Constructive interference (wave superposition)",
        "symbols": ["⊕_s"],
    },
    "symatics:⊖": {
        "description": "Destructive interference (phase inversion)",
        "symbols": ["⊖"],
    },
    "symatics:⊗": {
        "description": "Symatic tensor binding / coherence coupling",
        "symbols": ["⊗_s"],
    },
    "symatics:⋈": {
        "description": "Phase-join operator (φ-parametric interference)",
        "symbols": ["⋈"],
    },
    "symatics:⟲": {
        "description": "Resonant reflection / recursive resonance",
        "symbols": ["⟲"],
    },
    "symatics:↺": {
        "description": "Alias of ⟲ for self-reflective resonance",
        "symbols": ["↺"],
    },
    "symatics:cancel": {
        "description": "Cancels active vibration field",
        "symbols": ["cancel"],
    },
    "symatics:damping": {
        "description": "Applies damping factor to oscillatory modes",
        "symbols": ["damping"],
    },
    "symatics:resonance": {
        "description": "Triggers resonance amplification effect",
        "symbols": ["resonance"],
    },
    "symatics:⟁": {
        "description": "Dimensional lock / boundary test operator",
        "symbols": ["⟁"],
    },
    "symatics:⌬": {
        "description": "Compression lens / phase reduction modifier",
        "symbols": ["⌬"],
    },

    # ─── Control / Flow ─────────────────
    "control:⧖": {
        "description": "Temporal delay / deferred execution",
        "symbols": ["⧖"],
    },
    "control:→": {
        "description": "Flow implication / runtime trigger",
        "symbols": ["→_c"],
    },
    "control:⟲": {
        "description": "Control reflection / update loop",
        "symbols": ["⟲_c"],
    },

    # ─── Math / Physics ─────────────────
    "math:∇": {
        "description": "Gradient / divergence operator",
        "symbols": ["∇"],
    },
    "physics:⊗": {
        "description": "Physical tensor product (field combination)",
        "symbols": ["⊗_p"],
    },
    "physics:≈": {
        "description": "Physical coherence or similarity measure",
        "symbols": ["≈"],
    },

    # ─── Photon ─────────────────────────
    "photon:⊙": {
        "description": "Photon emission / absorption operator",
        "symbols": ["⊙"],
    },
    "photon:≈": {
        "description": "Photon-wave equivalence / coherence mapping",
        "symbols": ["≈", "~"],
    },
    "photon:primitive": {
        "description": "Photon primitive construct (atomic glyph)",
        "symbols": ["photon"],
    },
    "photon:wave": {
        "description": "Wave primitive construct (coherent field)",
        "symbols": ["wave"],
    },
}