# File: backend/modules/tests/test_instruction_registry.py
# -*- coding: utf-8 -*-
import pytest
import warnings

from backend.codexcore_virtual import instruction_registry as ir


def test_list_instructions_contains_domain_tags():
    """Registry should only expose domain-tagged ops as canonical keys."""
    instrs = ir.registry.list_instructions()
    # Check at least core ops
    assert any(k.startswith("logic:") for k in instrs)
    assert any(k.startswith("control:") for k in instrs)


def test_alias_redirects_with_warning():
    """Raw glyphs (⊕) should redirect to canonical key (logic:⊕)."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = ir.registry.execute("⊕", "DATA")
        assert "[STORE]" in result
        assert any("redirected" in str(msg.message) for msg in w)


def test_execute_v2_domain_tagged():
    """Domain-tagged execution should succeed cleanly."""
    result = ir.registry.execute_v2("control:⟲", "X")
    assert "[REFLECT]" in result


def test_unknown_symbol_raises():
    """Unknown symbols must raise KeyError."""
    with pytest.raises(KeyError):
        ir.registry.execute("???", "data")


def test_physics_handlers_raise_without_pk():
    """Physics handlers should raise RuntimeError if physics_kernel is missing."""
    with pytest.raises(RuntimeError):
        ir.registry.execute_v2("physics:∇", field="f", coords=["x", "y"])