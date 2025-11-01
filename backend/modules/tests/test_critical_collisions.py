# backend/modules/tests/test_critical_collisions.py

import pytest

from backend.modules.glyphos.codexlang_translator import parse_action_expr, translate_node
from backend.modules.codex.collision_resolver import resolve_collision


# ────────────────────────────────────────────────
# A1: ⊗ collisions (logic vs physics vs symatics)
# ────────────────────────────────────────────────

def test_tensor_collision_default_logic():
    """Bare ⊗ should resolve to logic:⊗ by priority."""
    expr = "⊗(A, B)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "logic:⊗"


def test_tensor_collision_physics_alias():
    """⊗_p should explicitly resolve to physics:⊗."""
    expr = "⊗_p(A, B)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "physics:⊗"


def test_tensor_collision_symatics_alias():
    """⊗_s should explicitly resolve to symatics:⊗."""
    expr = "⊗_s(A, B)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "symatics:⊗"


# ────────────────────────────────────────────────
# A2: ∇ collisions (math vs compressor)
# ────────────────────────────────────────────────

def test_nabla_collision_default_math():
    """Bare ∇ should resolve to math:∇ (default priority)."""
    expr = "∇(f)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "math:∇"


@pytest.mark.skip(reason="compressor:∇ not yet implemented")
def test_nabla_collision_future_compressor():
    """Future scope: ∇ may resolve to compressor:∇ in compressor context."""
    assert resolve_collision("∇", context="compressor") == "compressor:∇"


# ────────────────────────────────────────────────
# A3: ↔ collisions (logic vs quantum)
# ────────────────────────────────────────────────

def test_equivalence_collision_default_logic():
    """Bare ↔ should resolve to logic:↔ (logic outranks quantum)."""
    expr = "↔(P, Q)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "logic:↔"


def test_equivalence_collision_quantum_context():
    """Resolver should allow forcing ↔ -> quantum:↔ with context."""
    assert resolve_collision("↔", context="quantum") == "quantum:↔"


# ────────────────────────────────────────────────
# A4: ⊕ collisions (logic vs quantum)
# ────────────────────────────────────────────────

def test_xor_collision_default_logic():
    """Bare ⊕ should resolve to logic:⊕ (logic outranks quantum)."""
    expr = "⊕(X, Y)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "logic:⊕"


def test_xor_collision_quantum_alias():
    """⊕_q should explicitly resolve to quantum:⊕."""
    expr = "⊕_q(X, Y)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "quantum:⊕"


# ────────────────────────────────────────────────
# A5: ⧖ collisions (control vs quantum)
# ────────────────────────────────────────────────

def test_delay_default_control():
    """Bare ⧖ should resolve to control:⧖ (default priority)."""
    expr = "⧖(Task)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "control:⧖"


@pytest.mark.skip(reason="quantum:⧖ not yet implemented")
def test_delay_quantum_future():
    """Future scope: ⧖ may resolve to quantum:⧖ in quantum context."""
    assert resolve_collision("⧖", context="quantum") == "quantum:⧖"


# ────────────────────────────────────────────────
# A6: ≈ / ~ alias (photon)
# ────────────────────────────────────────────────

def test_wave_equivalence_aliases():
    """≈ and ~ should both resolve to photon:≈."""
    expr1 = "≈(ψ)"
    expr2 = "~(ψ)"

    parsed1 = parse_action_expr(expr1)
    parsed2 = parse_action_expr(expr2)

    t1 = translate_node(parsed1)
    t2 = translate_node(parsed2)

    assert t1["op"] == "photon:≈"
    assert t2["op"] == "photon:≈"