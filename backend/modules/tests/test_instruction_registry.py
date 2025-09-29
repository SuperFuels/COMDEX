# File: backend/modules/tests/test_instruction_registry.py
# -*- coding: utf-8 -*-
import pytest
import warnings

from backend.codexcore_virtual import instruction_registry as ir

# ----------------------
# Registry Shape
# ----------------------

def test_list_instructions_contains_domain_tags():
    """Registry should only expose domain-tagged ops as canonical keys."""
    instrs = ir.registry.list_instructions()
    # Check at least core ops
    assert any(k.startswith("logic:") for k in instrs)
    assert any(k.startswith("control:") for k in instrs)
    assert any(k.startswith("memory:") for k in instrs)


# ----------------------
# Alias + Redirection
# ----------------------

def test_alias_redirects_with_warning():
    """Raw glyphs (⊕) should redirect to canonical key (logic:⊕)."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = ir.registry.execute("⊕", "DATA")
        assert "[STORE]" in result
        assert any("redirected" in str(msg.message) for msg in w)


# ----------------------
# Logic + Memory Ops
# ----------------------

def test_execute_v2_domain_tagged_reflect():
    """Domain-tagged execution should succeed cleanly (control:⟲)."""
    result = ir.registry.execute_v2("control:⟲", "X")
    assert "[REFLECT]" in result

def test_logic_negation_and_store():
    result = ir.registry.execute_v2("logic:⊕", "abc")
    assert "[STORE]" in result

    result = ir.registry.execute_v2("logic:¬", x=True)
    assert result == {"neg": True}

def test_memory_recall():
    result = ir.registry.execute_v2("memory:↺", data="xyz")
    assert "[RECALL]" in result


# ----------------------
# Physics Ops
# ----------------------

@pytest.mark.parametrize("symbol,args", [
    ("physics:∇", {"field": [1, 2, 3], "coords": [0, 1, 2]}),
    ("physics:Δ", {"field": [1, 2, 3], "coords": [0, 1, 2]}),
    ("physics:×", {"A": [1, 0, 0], "B": [0, 1, 0]}),
])
def test_physics_ops_safe(symbol, args):
    """
    Physics ops should raise RuntimeError if physics_kernel is missing,
    otherwise return something (dict, number, etc.).
    """
    try:
        result = ir.registry.execute_v2(symbol, **args)
        assert result is not None
    except RuntimeError as e:
        assert "physics_kernel not available" in str(e)


# ----------------------
# Error Handling
# ----------------------

def test_unknown_symbol_raises():
    """Unknown symbols must raise KeyError."""
    with pytest.raises(KeyError):
        ir.registry.execute("???", "data")