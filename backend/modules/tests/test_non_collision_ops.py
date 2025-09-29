import pytest

from backend.modules.glyphos.codexlang_translator import parse_action_expr, translate_node


def check(expr: str, expected_op: str):
    """Helper: parse CodexLang action expr and check final op."""
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)

    # If parser gave us just a string (like "ψ⟩" or "H"), wrap into dict
    if isinstance(translated, str):
        translated = {"op": translate_node({"op": translated})["op"]}

    assert translated["op"] == expected_op
    return translated


# ────────────────────────────────────────────────
# Control
# ────────────────────────────────────────────────

def test_control_rotate():
    check("⟲(A)", "control:⟲")

def test_control_delay():
    check("⧖(X)", "control:⧖")


# ────────────────────────────────────────────────
# Quantum Scoped Symbols
# ────────────────────────────────────────────────

@pytest.mark.parametrize("expr,expected", [
    ("ψ⟩", "quantum:ket"),
    ("⟨ψ|", "quantum:bra"),
    ("Â", "quantum:A"),
    ("H", "quantum:H"),
    ("[(X)]", "quantum:commutator_open"),  # just symbol check
    ("](X)", "quantum:commutator_close"),
])
def test_quantum_symbols(expr, expected):
    check(f"{expr}", expected)


# ────────────────────────────────────────────────
# Photon
# ────────────────────────────────────────────────

def test_photon_absorption():
    check("⊙(beam)", "photon:⊙")

def test_photon_equivalence_aliases():
    assert check("≈(wave)", "photon:≈")
    assert check("~(wave)", "photon:≈")


# ────────────────────────────────────────────────
# Symatics
# ────────────────────────────────────────────────

@pytest.mark.parametrize("expr,expected", [
    ("cancel(x)", "symatics:cancel"),
    ("damping(y)", "symatics:damping"),
    ("resonance(z)", "symatics:resonance"),
])
def test_symatics_ops(expr, expected):
    check(expr, expected)


# ────────────────────────────────────────────────
# Logic (unambiguous set)
# ────────────────────────────────────────────────

@pytest.mark.parametrize("expr,expected", [
    ("¬(P)", "logic:¬"),
    ("∧(A,B)", "logic:∧"),
    ("∨(X,Y)", "logic:∨"),
    ("→(P,Q)", "logic:→"),
])
def test_logic_ops(expr, expected):
    check(expr, expected)