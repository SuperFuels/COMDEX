# File: backend/tests/test_introspection_index.py

import pytest
from backend.modules.knowledge_graph.indexes import introspection_index
from backend.modules.state_manager import reset_container_state, get_active_container

def setup_function():
    # Reset container before each test
    reset_container_state()

def test_add_basic_introspection_event():
    description = "Realized contradiction between goal and behavior."
    source = "awareness_engine"
    event_id = introspection_index.add_introspection_event(
        description=description,
        source_module=source
    )

    container = get_active_container()
    entries = container["indexes"].get("introspection_index", [])
    assert len(entries) == 1
    entry = entries[0]

    assert entry["id"] == event_id
    assert entry["description"] == description
    assert entry["source"] == source
    assert entry["type"] == "introspection"
    assert isinstance(entry["hash"], str)
    assert "timestamp" in entry

def test_add_full_metadata_event():
    description = "Detected low confidence on ethics planning task."
    source = "codex_executor"
    tags = ["ethics", "planning", "low_confidence"]
    confidence = 0.35
    blindspot = "ethics_bias"
    glyph_ref = "glyph_abc123"
    persona = "strategist_v2"

    event_id = introspection_index.add_introspection_event(
        description=description,
        source_module=source,
        tags=tags,
        confidence=confidence,
        blindspot_trigger=blindspot,
        glyph_trace_ref=glyph_ref,
        persona_state=persona
    )

    container = get_active_container()
    entries = container["indexes"].get("introspection_index", [])
    assert len(entries) == 1
    entry = entries[0]

    assert entry["id"] == event_id
    assert entry["description"] == description
    assert entry["tags"] == tags
    assert entry["confidence"] == confidence
    assert entry["blindspot_trigger"] == blindspot
    assert entry["glyph_trace"] == glyph_ref
    assert entry["persona"] == persona