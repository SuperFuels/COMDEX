# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_glyph_registry.py
"""
Test: Glyph Registry Delegation
-------------------------------
Ensures glyph:* ops are correctly routed through the
global instruction_registry, not hardcoded handlers.
"""

import pytest
from backend.modules.glyphos.glyph_dispatcher import GlyphDispatcher
from backend.modules.consciousness.state_manager import StateManager
from backend.codexcore_virtual import instruction_registry as ir


class DummyState(StateManager):
    """Minimal dummy context for glyph ops (no real state)."""
    def __init__(self):
        super().__init__()
        self._teleported = None
        self._container = {"path": "dummy_path"}

    def teleport(self, dest):
        self._teleported = dest

    def get_current_container(self):
        return self._container


def test_glyph_teleport_via_registry():
    ctx = DummyState()
    dispatcher = GlyphDispatcher(ctx)

    glyph = {"action": "teleport", "target": "Omega"}
    result = dispatcher.dispatch(glyph)

    assert result["status"] == "ok"
    assert result["teleported_to"] == "Omega"
    assert ctx._teleported == "Omega"


def test_glyph_log_via_registry():
    ctx = DummyState()
    dispatcher = GlyphDispatcher(ctx)

    msg = "HelloGlyph"
    glyph = {"action": "log", "message": msg}
    result = dispatcher.dispatch(glyph)

    assert result["status"] == "ok"
    assert result["log"] == msg


def test_glyph_run_mutation_via_registry(monkeypatch):
    ctx = DummyState()
    dispatcher = GlyphDispatcher(ctx)

    called = {}

    def fake_generate_mutation(module, reason):
        called["module"] = module
        called["reason"] = reason
        return True

    monkeypatch.setattr(
        "backend.modules.dna_chain.crispr_ai.generate_mutation_proposal",
        fake_generate_mutation,
    )

    glyph = {"action": "run_mutation", "module": "test_module", "reason": "unit test"}
    result = dispatcher.dispatch(glyph)

    assert result["status"] == "ok"
    assert called["module"] == "test_module"
    assert called["reason"] == "unit test"