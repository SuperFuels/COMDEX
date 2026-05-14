# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_registry_bridge.py
import pytest

from backend.core.registry_bridge import registry_bridge


def test_raw_symatics_symbol_resolves_and_executes():
    """Raw ⊕ should resolve to symatics:⊕ via bridge and execute."""
    result = registry_bridge.resolve_and_execute("⊕", "A", "B")
    assert isinstance(result, dict) or isinstance(result, str)
    # must indicate it ran, not stub
    assert "unhandled_op" not in result


def test_unknown_symbol_falls_back_stub():
    """Unknown glyph should produce a stub response with warning."""
    res = registry_bridge.resolve_and_execute("???", foo=1)
    assert isinstance(res, dict)
    assert res.get("unhandled_op") == "???"


def test_has_handler_alias_and_canonical():
    """has_handler should work for both raw glyph and canonical key."""
    assert registry_bridge.has_handler("⊕")
    assert registry_bridge.has_handler("symatics:⊕")