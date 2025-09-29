import pytest
from backend.modules.codex.collision_resolver import (
    resolve_collision,
    resolve_op,
    is_collision,
)


def test_is_collision_flags_known_symbols():
    assert is_collision("⊗") is True
    assert is_collision("⊕") is True
    assert is_collision("∇") is True
    assert is_collision("↔") is True
    assert is_collision("∧") is False  # not ambiguous


def test_resolve_collision_with_context():
    # Explicit context should win
    assert resolve_collision("⊗", context="physics") == "physics:⊗"
    assert resolve_collision("⊕", context="quantum") == "quantum:⊕"
    assert resolve_collision("⊗", context="symatics") == "symatics:⊗"


def test_resolve_collision_with_priority_order():
    # No context → fallback to PRIORITY_ORDER
    # "⊗" has options [logic, physics, symatics], priority says logic first
    assert resolve_collision("⊗") == "logic:⊗"
    # "⊕" → logic preferred over quantum
    assert resolve_collision("⊕") == "logic:⊕"
    # "↔" → logic preferred over quantum
    assert resolve_collision("↔") == "logic:↔"


def test_resolve_collision_unknown_symbol():
    # Non-collision or unknown → None
    assert resolve_collision("∧") is None
    assert resolve_collision("???") is None


# 🔵 Alias and resolve_op tests
def test_resolve_op_aliases():
    # Aliases should map directly
    assert resolve_op("⊕_q") == "quantum:⊕"
    assert resolve_op("⊗_p") == "physics:⊗"
    assert resolve_op("⊗_s") == "symatics:⊗"
    assert resolve_op("~") == "photon:≈"


def test_resolve_op_with_collision_priority():
    # Ambiguous symbol → should follow PRIORITY_ORDER
    assert resolve_op("⊗") == "logic:⊗"  # logic wins
    assert resolve_op("⊕") == "logic:⊕"  # logic wins
    assert resolve_op("↔") == "logic:↔"  # logic wins


def test_resolve_op_fallback():
    # Unknown operator → returned as-is
    assert resolve_op("??") == "??"