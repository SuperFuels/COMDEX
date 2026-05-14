import warnings
import pytest

import backend.codexcore_virtual.symbolic_instruction_set as sis


# ─── Basic Raw Symbols ─────────────────────────────────────────────────────────

def test_raw_symbol_add():
    assert sis.is_valid_opcode("⊕")
    op = sis.get_opcode("⊕")
    # Legacy raw symbol maps to logic:⊕
    assert op == "logic:⊕"


def test_raw_symbol_loop():
    assert sis.is_valid_opcode("⟲")
    op = sis.get_opcode("⟲")
    assert op == "control:⟲"


def test_raw_symbol_sequence():
    assert sis.is_valid_opcode("->")
    op = sis.get_opcode("->")
    assert op == "logic:->"


# ─── Canonical Domain-Tagged ───────────────────────────────────────────────────

def test_canonical_logic_add():
    assert sis.is_valid_opcode("logic:⊕")
    op = sis.get_opcode("logic:⊕")
    assert op == "logic:⊕"


def test_canonical_control_loop():
    assert sis.is_valid_opcode("control:⟲")
    op = sis.get_opcode("control:⟲")
    assert op == "control:⟲"


# ─── Warning Check For Legacy Use ──────────────────────────────────────────────

def test_warning_on_raw_symbol():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _ = sis.get_opcode("⊕")
        assert any("compat" in str(wi.message).lower() for wi in w)


# ─── Handler Map Integrity ─────────────────────────────────────────────────────

def test_handler_map_contains_canonical():
    # Ensure canonical keys exist in handler map
    handlers = sis.list_symbolic_opcodes()
    assert "logic:⊕" in handlers
    assert "control:⟲" in handlers
    assert "logic:->" in handlers