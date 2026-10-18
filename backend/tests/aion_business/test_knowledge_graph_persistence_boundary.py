from __future__ import annotations

import pytest

from backend.modules.knowledge_graph import knowledge_graph_writer as module
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter


def _writer(monkeypatch: pytest.MonkeyPatch) -> KnowledgeGraphWriter:
    monkeypatch.setattr(module, "add_to_index", lambda *_args, **_kwargs: None)
    writer = object.__new__(KnowledgeGraphWriter)
    writer.inject_glyph = lambda **_kwargs: None
    return writer


def test_entanglement_refuses_undeclared_sqlite_fallback(monkeypatch):
    writer = _writer(monkeypatch)

    with pytest.raises(RuntimeError, match="knowledge_graph_event_authority_required"):
        writer.write_entanglement_entry("private-a", "private-b")


def test_entanglement_uses_injected_governed_event_authority(monkeypatch):
    writer = _writer(monkeypatch)
    events = []
    writer.append_event = lambda **payload: events.append(payload)

    writer.write_entanglement_entry("private-a", "private-b")

    assert len(events) == 1
    assert events[0]["type"] == "entanglement"
    assert events[0]["payload"]["metadata"] == {
        "from": "private-a",
        "to": "private-b",
        "container_a": "private-a",
        "container_b": "private-b",
    }
