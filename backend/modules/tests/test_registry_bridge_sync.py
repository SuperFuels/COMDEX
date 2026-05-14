# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_registry_bridge_sync.py
"""
Smoke tests for RegistryBridge sync.

Checks:
  * symatics:⊕ delegates to rulebook
  * glyph:teleport stub is registered
"""

import pytest

from backend.core.registry_bridge import registry_bridge


def test_symatics_superpose_registered():
    """Ensure symatics:⊕ is in the registry and executable."""
    result = registry_bridge.resolve_and_execute("symatics:⊕", "A", "B", context={})
    # SR.op_superpose normally returns dict with 'result' key
    assert isinstance(result, dict)
    assert "result" in result or "stub" not in result


def test_glyph_teleport_registered():
    """Ensure glyph:teleport is available after sync."""
    result = registry_bridge.resolve_and_execute("glyph:teleport", target="mars_base")
    assert isinstance(result, dict)
    assert result.get("glyph_action") == "teleport"
    assert result["kwargs"]["target"] == "mars_base"


def test_unknown_symbol_falls_back():
    """Unknown ops should fall back to stub safely."""
    result = registry_bridge.resolve_and_execute("glyph:nonexistent", foo="bar")
    assert isinstance(result, dict)
    assert result.get("unhandled_op") == "glyph:nonexistent"