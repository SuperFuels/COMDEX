import pytest
from backend.modules.knowledge_graph.indexes import dream_index
from backend.modules.state_manager import get_active_container


def test_add_basic_dream():
    container = get_active_container()
    container["indexes"] = {}  # Reset indexes

    dream_str = "🌌 Initiate holographic expansion via memory pulse"
    dream_id = dream_index.add_dream(dream=dream_str)

    assert dream_id is not None
    assert "indexes" in container
    assert "dream_index" in container["indexes"]
    assert any(d["id"] == dream_id for d in container["indexes"]["dream_index"])
    assert container["indexes"]["dream_index"][0]["content"] == dream_str
    assert "rubric_report" in container


def test_add_dream_with_coordinates():
    container = get_active_container()
    container["indexes"] = {}

    dream_str = "Visualize multi-agent replay across entangled zones"
    coords = {"x": 3.1, "y": -0.2, "z": 5.7}
    dream_id = dream_index.add_dream(
        dream=dream_str,
        holographic_hint=coords,
        source_plugin="dream_core",
        related_goal="goal-123",
        glyph_trace="trace-xyz"
    )

    dream_entry = next(d for d in container["indexes"]["dream_index"] if d["id"] == dream_id)

    assert dream_entry["coordinates"] == coords
    assert dream_entry["metadata"]["source"] == "dream_core"
    assert dream_entry["metadata"]["goal_ref"] == "goal-123"
    assert dream_entry["trace"] == "trace-xyz"


def test_dream_rubric_report_structure():
    container = get_active_container()
    container["indexes"] = {}

    dream_index.add_dream("🌀 Simulate future mutation vector for collapse escape")

    report = container.get("rubric_report", {})
    assert isinstance(report, dict)
    assert all(k in report for k in [
        "deduplication",
        "container_awareness",
        "semantic_metadata",
        "timestamps",
        "plugin_compatibility",
        "search_summary_api",
        "export_format",
        "dc_injection"
    ])