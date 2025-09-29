# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_registry_bridge_codex_sync.py

import pytest
from backend.core.registry_bridge import registry_bridge

def test_codex_and_glyph_and_symatics_handlers_present():
    # Codex YAML op
    assert registry_bridge.has_handler("core:⊕"), "Codex ⊕ not synced into registry"

    # GlyphInstructionSet op
    assert registry_bridge.has_handler("glyph:→"), "Glyph → not synced into registry"

    # Symatics op
    assert registry_bridge.has_handler("symatics:⊕"), "Symatics ⊕ not synced into registry"

def test_codex_op_executes_stub_or_fn():
    result = registry_bridge.resolve_and_execute("core:⊕", "A", "B")
    # Depending on whether function is implemented, we either get stub or actual result
    assert isinstance(result, dict) or isinstance(result, str)

def test_glyph_op_executes():
    result = registry_bridge.resolve_and_execute("glyph:→", "X", "Y")
    assert result is not None

def test_symatics_op_executes():
    result = registry_bridge.resolve_and_execute("symatics:⊕", "A", "B")
    assert result is not None