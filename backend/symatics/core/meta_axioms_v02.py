"""
Symatics v2.0 Meta-Axioms Layer
Tessaris / CodexCore 2025
Defines the foundational Geometry->Computation laws (G-L-E-I-C-X)
in executable structured form, with runtime registry export.
"""

# -------------------------------------------------------------------------
# Meta-Axiom Definitions
# -------------------------------------------------------------------------

META_AXIOMS = [
    # --- Geometry ---
    {
        "id": "G1",
        "domain": "Geometry",
        "title": "Phase Space Primacy",
        "statement": (
            "All metric geometry arises from resonance topology; "
            "space and distance are projections of phase separations "
            "between coherent waves."
        ),
        "expression": "π(space) := ⟲(phase_coherence)",
        "validated_by": ["validate_pi_s_closure"],
    },
    {
        "id": "G2",
        "domain": "Geometry",
        "title": "Phase Closure (πs Constant)",
        "statement": (
            "πs defines the minimal closure angle of self-referential resonance; "
            "metric π is a derived projection of πs."
        ),
        "expression": "∮ Δφ = 2πs n",
        "validated_by": ["validate_pi_s_closure"],
    },

    # --- Logic ---
    {
        "id": "L1",
        "domain": "Logic",
        "title": "Deterministic Collapse",
        "statement": (
            "Measurement (μ) yields a determinate projection for any stable resonance; "
            "apparent randomness is unresolved superposition."
        ),
        "symbolic": "μ(⟲ψ) -> ψ′ where ψ′ = π(μ(⟲ψ))",
    },
    {
        "id": "L2",
        "domain": "Logic",
        "title": "Entangled Causality",
        "statement": (
            "Entanglement (↔) establishes bidirectional influence; "
            "causality is symmetric across collapse boundaries."
        ),
        "symbolic": "A ↔ B  ->  μ(A) ⇔ μ(B)",
    },

    # --- Energy ---
    {
        "id": "E1",
        "domain": "Energy",
        "title": "Resonant Inertia",
        "statement": (
            "Mass is resistance to phase collapse; "
            "energy is the rate of phase rotation in resonance space."
        ),
        "symbolic": "E = ħ dφ/dt",
    },

    # --- Information ---
    {
        "id": "I1",
        "domain": "Information",
        "title": "Coherent Information",
        "statement": (
            "Information is preserved phase coherence, not discrete entropy."
        ),
        "symbolic": "I ∝ |⟨ψ|ψ⟩|2",
    },

    # --- Cognition ---
    {
        "id": "C1",
        "domain": "Cognition",
        "title": "Conscious Measurement Loop",
        "statement": (
            "Consciousness is recursive resonance measurement: Ψ ↔ μ(⟲Ψ)."
        ),
        "symbolic": "Ψ ↔ μ(⟲Ψ)",
    },

    # --- Computation ---
    {
        "id": "X1",
        "domain": "Computation",
        "title": "Phase-Closure Halting Condition",
        "statement": (
            "A computation halts when the system achieves πs closure; "
            "symbolic termination equals phase coherence completion."
        ),
        "symbolic": "halt ⇔ ∮ Δφ = 2πs n",
        "validated_by": ["validate_pi_s_closure"],
    },
]


# -------------------------------------------------------------------------
# Runtime Law Registry
# -------------------------------------------------------------------------

# Registry is dynamically extended by validators under core/validators/*
LAW_REGISTRY = {}

# Populate registry with placeholder validator metadata if not yet loaded
for axiom in META_AXIOMS:
    for v in axiom.get("validated_by", []):
        LAW_REGISTRY[v] = {
            "axiom_id": axiom["id"],
            "domain": axiom["domain"],
            "title": axiom["title"],
            "validate": lambda expr, ctx=None, name=v: {"passed": True, "law": name},
        }


# -------------------------------------------------------------------------
# Exports
# -------------------------------------------------------------------------

__all__ = ["META_AXIOMS", "LAW_REGISTRY"]