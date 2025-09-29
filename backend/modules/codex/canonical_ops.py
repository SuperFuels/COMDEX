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
    "↔": "quantum:↔",
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
# Operator metadata (for docs & auto-reference)
# ────────────────────────────────────────────────

OP_METADATA = {
    # Logic
    "logic:⊕": {"description": "Combines two symbolic values"},
    "logic:⊗": {"description": "Multiplies symbolic structures"},
    "logic:¬": {"description": "Logical negation"},
    "logic:∨": {"description": "Logical OR"},
    "logic:∧": {"description": "Logical AND"},
    "logic:→": {"description": "Logical implication"},

    # Quantum
    "quantum:↔": {"description": "Checks bidirectional equivalence"},
    "quantum:⊕": {"description": "Quantum XOR-like operation"},
    "quantum:A": {"description": "Quantum operator Â"},
    "quantum:H": {"description": "Hadamard gate"},
    "quantum:ket": {"description": "Quantum ket state"},
    "quantum:bra": {"description": "Quantum bra state"},
    "quantum:commutator_open": {"description": "Quantum commutator start"},
    "quantum:commutator_close": {"description": "Quantum commutator end"},

    # Symatics
    "symatics:⊗": {"description": "Symatics tensor product"},
    "symatics:cancel": {"description": "Cancels a vibration or resonance"},
    "symatics:damping": {"description": "Applies damping factor"},
    "symatics:resonance": {"description": "Triggers resonance effect"},

    # Control
    "control:⟲": {"description": "Performs self-mutation or update"},
    "control:⧖": {"description": "Delays execution of a symbol"},

    # Math
    "math:∇": {"description": "Gradient / divergence operator"},

    # Photon
    "photon:≈": {"description": "Photon wave equivalence"},
    "photon:⊙": {"description": "Photon absorption/emission operator"},

    # Physics
    "physics:⊗": {"description": "Physical tensor product"},
}