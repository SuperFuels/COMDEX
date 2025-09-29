# backend/modules/codex/canonical_ops.py

# ────────────────────────────────────────────────
# Canonical operator mapping
# ────────────────────────────────────────────────

CANONICAL_OPS = {
    # Logic
    "⊕": "logic:⊕",
    "⊗": "logic:⊗",
    "∧": "logic:∧",
    "∨": "logic:∨",
    "¬": "logic:¬",
    "→": "logic:→",

    # Quantum
    # ⚠️ removed "↔" here → ambiguous, handled by COLLISIONS
    "⊕_q": "quantum:⊕",
    "ψ⟩": "quantum:ket",
    "⟨ψ|": "quantum:bra",
    "Â": "quantum:A",
    "H": "quantum:H",
    "[": "quantum:commutator_open",
    "]": "quantum:commutator_close",

    # Symatics
    "⊗_s": "symatics:⊗",
    "cancel": "symatics:cancel",
    "damping": "symatics:damping",
    "resonance": "symatics:resonance",

    # Math / Physics
    "∇": "math:∇",
    "⊗_p": "physics:⊗",

    # Control / Flow
    "⧖": "control:⧖",
    "⟲": "control:⟲",

    # Photon
    "⊙": "photon:⊙",
    "≈": "photon:≈",
    "~": "photon:≈",
}

# ────────────────────────────────────────────────
# Collisions table (ambiguous ops only)
# ────────────────────────────────────────────────

COLLISIONS = {
    "⊗": ["logic:⊗", "physics:⊗", "symatics:⊗"],
    "⊕": ["logic:⊕", "quantum:⊕"],
    "↔": ["logic:↔", "quantum:↔"],
}

# ────────────────────────────────────────────────
# Operator metadata (with explicit symbols for stability)
# ────────────────────────────────────────────────

OP_METADATA = {
    # Logic
    "logic:⊕": {
        "description": "Logical XOR",
        "symbols": ["⊕"],
    },
    "logic:⊗": {
        "description": "Multiplies symbolic structures",
        "symbols": ["⊗"],
    },
    "logic:¬": {"description": "Logical negation", "symbols": ["¬"]},
    "logic:∨": {"description": "Logical OR", "symbols": ["∨"]},
    "logic:∧": {"description": "Logical AND", "symbols": ["∧"]},
    "logic:→": {"description": "Logical implication", "symbols": ["→"]},
    "logic:↔": {
        "description": "Logical equivalence (biconditional)",
        "symbols": ["↔"],
    },

    # Quantum
    "quantum:↔": {
        "description": "Quantum bidirectional equivalence",
        "symbols": ["↔"],
    },
    "quantum:⊕": {
        "description": "Quantum XOR-like operation",
        "symbols": ["⊕_q"],
    },
    "quantum:A": {"description": "Quantum operator Â", "symbols": ["Â"]},
    "quantum:H": {"description": "Hadamard gate", "symbols": ["H"]},
    "quantum:ket": {"description": "Quantum ket state", "symbols": ["ψ⟩"]},
    "quantum:bra": {"description": "Quantum bra state", "symbols": ["⟨ψ|"]},
    "quantum:commutator_open": {
        "description": "Quantum commutator start",
        "symbols": ["["],
    },
    "quantum:commutator_close": {
        "description": "Quantum commutator end",
        "symbols": ["]"],
    },

    # Symatics
    "symatics:⊗": {
        "description": "Symatics tensor product",
        "symbols": ["⊗_s"],
    },
    "symatics:cancel": {
        "description": "Cancels a vibration or resonance",
        "symbols": ["cancel"],
    },
    "symatics:damping": {
        "description": "Applies damping factor",
        "symbols": ["damping"],
    },
    "symatics:resonance": {
        "description": "Triggers resonance effect",
        "symbols": ["resonance"],
    },

    # Control
    "control:⟲": {
        "description": "Performs self-mutation or update",
        "symbols": ["⟲"],
    },
    "control:⧖": {
        "description": "Delays execution of a symbol",
        "symbols": ["⧖"],
    },

    # Math
    "math:∇": {
        "description": "Gradient / divergence operator",
        "symbols": ["∇"],
    },

    # Photon
    "photon:≈": {
        "description": "Photon wave equivalence",
        "symbols": ["≈", "~"],
    },
    "photon:⊙": {
        "description": "Photon absorption/emission operator",
        "symbols": ["⊙"],
    },

    # Physics
    "physics:⊗": {
        "description": "Physical tensor product",
        "symbols": ["⊗_p"],
    },
}