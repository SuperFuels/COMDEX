# backend/photon_algebra/tests/test_pp_roundtrip.py

import pytest
from hypothesis import given, strategies as st

from backend.tools.photon_pp import pp
from backend.photon_algebra.photon_parse import parse
from backend.photon_algebra.rewriter import normalize


# -------------------------------
# Hand-picked regression tests
# -------------------------------
@pytest.mark.parametrize("expr,expected_pretty", [
    # Distribution test
    ({"op": "⊗", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
     "a ⊗ (b ⊕ c)"),

    # Unary negation inside superposition
    ({"op": "⊕", "states": ["a", {"op": "¬", "state": "b"}]},
     "a ⊕ ¬b"),

    # Entanglement with grouped sum: a ↔ (b ⊕ c)
    ({"op": "↔", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
     "a ↔ (b ⊕ c)"),

    # Explicit parentheses: (a ↔ b) ⊕ c
    ({"op": "⊕", "states": [
        {"op": "↔", "states": ["a", "b"]},
        "c"
    ]},
     "(a ↔ b) ⊕ c"),

    # Star applied to negation
    ({"op": "★", "state": {"op": "¬", "state": "a"}},
     "★¬a"),

    # Cancellation
    ({"op": "⊖", "states": ["a", "b"]},
     "a ⊖ b"),

    # --- New inert meta-ops ---
    # Similarity a ≈ b
    ({"op": "≈", "states": ["a", "b"]},
     "a ≈ b"),

    # Containment a ⊂ b
    ({"op": "⊂", "states": ["a", "b"]},
     "a ⊂ b"),

    # Top / Bottom constants
    ({"op": "⊤"}, "⊤"),
    ({"op": "⊥"}, "⊥"),

    # Mixed with grouping: (a ≈ b) ⊕ c
    ({"op": "⊕", "states": [
        {"op": "≈", "states": ["a", "b"]},
        "c",
    ]},
     "(a ≈ b) ⊕ c"),

    # Mixed with grouping: a ⊂ (b ⊕ c)
    ({"op": "⊂", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
     "a ⊂ (b ⊕ c)"),
])
def test_roundtrip(expr, expected_pretty):
    pretty = pp(expr)
    parsed = parse(pretty)

    # Pretty-print must be exactly as expected
    assert pretty == expected_pretty, (
        f"Pretty mismatch: {expr} → {pretty}, expected {expected_pretty}"
    )

    # Normalized ASTs must match after roundtrip (double-normalize for stability)
    norm_expr = normalize(normalize(expr))
    norm_parsed = normalize(normalize(parsed))
    assert norm_expr == norm_parsed, (
        f"Roundtrip failed for {expr} → {pretty} → {parsed}\n"
        f"Expected: {norm_expr}\n"
        f"Got: {norm_parsed}"
    )

# -------------------------------
# Hypothesis property-based test
# -------------------------------

atoms = st.sampled_from(["a", "b", "c", "x", "y", "z", "p", "q", "r"])

# -------------------------------
# Hypothesis property-based test
# -------------------------------

atoms = st.sampled_from(["a", "b", "c", "x", "y", "z", "p", "q", "r"])

def photon_exprs(depth=3):
    if depth == 0:
        return atoms

    return st.one_of(
        atoms,
        st.builds(lambda s: {"op": "⊕", "states": s},
                  st.lists(photon_exprs(depth-1), min_size=2, max_size=3)),
        st.builds(lambda a, b: {"op": "⊗", "states": [a, b]},
                  photon_exprs(depth-1), photon_exprs(depth-1)),
        st.builds(lambda a, b: {"op": "⊖", "states": [a, b]},
                  photon_exprs(depth-1), photon_exprs(depth-1)),
        st.builds(lambda a, b: {"op": "↔", "states": [a, b]},
                  photon_exprs(depth-1), photon_exprs(depth-1)),
        st.builds(lambda s: {"op": "¬", "state": s},
                  photon_exprs(depth-1)),
        st.builds(lambda s: {"op": "★", "state": s},
                  photon_exprs(depth-1)),
        st.just({"op": "∅"}),

        # --- New inert meta-ops ---
        st.builds(lambda a, b: {"op": "≈", "states": [a, b]},
                  photon_exprs(depth-1), photon_exprs(depth-1)),
        st.builds(lambda a, b: {"op": "⊂", "states": [a, b]},
                  photon_exprs(depth-1), photon_exprs(depth-1)),
        st.just({"op": "⊤"}),
        st.just({"op": "⊥"}),
    )


@given(photon_exprs())
def test_hypothesis_roundtrip(expr):
    pretty = pp(expr)
    parsed = parse(pretty)

    norm1 = normalize(normalize(expr))
    norm2 = normalize(normalize(parsed))

    if norm1 != norm2:  # 🔍 debug dump
        print("\n--- DEBUG ROUNDTRIP MISMATCH ---")
        print("Original expr: ", expr)
        print("Pretty:        ", pretty)
        print("Parsed:        ", parsed)
        print("Norm1:         ", norm1)
        print("Norm2:         ", norm2)
        print("-------------------------------")

    assert norm1 == norm2, (
        f"Hypothesis roundtrip failed for {expr} → {pretty} → {parsed}\n"
        f"Expected: {norm1}\n"
        f"Got: {norm2}"
    )