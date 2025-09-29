# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_glyph_dispatcher.py
import pytest
from backend.modules.glyphos.glyph_dispatcher import GlyphDispatcher
from backend.core.registry_bridge import registry_bridge


class DummyStateManager:
    def __init__(self):
        self.teleported = None
        self.container = {"path": "/tmp/container"}

    def teleport(self, dest):
        self.teleported = dest

    def get_current_container(self):
        return self.container


def test_registry_routed_action(monkeypatch):
    """If action matches registry handler, GlyphDispatcher should route it."""
    gd = GlyphDispatcher(DummyStateManager())

    # monkeypatch registry to handle "glyph:teleport"
    def fake_handler(ctx, *args, **kwargs):
        return {"ok": True, "args": args, "kwargs": kwargs}

    registry_bridge.instruction_registry.override("glyph:teleport", fake_handler)
    registry_bridge.instruction_registry.alias("teleport", "glyph:teleport")

    result = gd.dispatch({"action": "teleport", "target": "mars"})
    assert isinstance(result, dict)
    assert result["ok"] is True


def test_fallback_log_action(capsys):
    """Legacy action 'log' should still go through _handle_log."""
    gd = GlyphDispatcher(DummyStateManager())
    gd.dispatch({"action": "log", "message": "hello world"})

    out = capsys.readouterr().out
    assert "Glyph Log" in out