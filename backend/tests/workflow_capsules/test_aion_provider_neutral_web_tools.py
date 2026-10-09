from backend.modules.aion_fabric.model_tool_runtime import (
    ConnectedModelToolRuntime,
    requires_current_web_evidence,
    web_research_query,
)
from backend.modules.local_node.tool_registry import build_default_tool_registry


def test_current_information_detection_uses_newest_turn_only() -> None:
    assert requires_current_web_evidence("Search the web for recent El Nino coverage")
    assert requires_current_web_evidence("What is the latest coverage?")
    assert not requires_current_web_evidence("User: search the web\n\nUser: what is 2 + 2?")
    assert web_research_query("search the web and find out anything recent about El Nino") == (
        "recent about El Nino"
    )


def test_same_research_context_is_rendered_for_any_connected_model() -> None:
    runtime = ConnectedModelToolRuntime(evidence_search=lambda _query: [{
        "title": "Official update",
        "url": "https://example.com/update",
        "summary": "Current verified information.",
        "published_at": "2026-10-07",
    }])
    context = runtime.prepare("Find the latest official update")
    assert context is not None
    assert context.provider_neutral is True
    rendered = context.render_for_model()
    assert "Do not say that you cannot browse" in rendered
    assert "https://example.com/update" in rendered


def test_registry_exposes_enabled_provider_neutral_research_tool() -> None:
    tool = next(item for item in build_default_tool_registry() if item.tool_id == "tool.web.search_read.v1")
    assert tool.enabled is True
    assert tool.requires_approval is False
    assert tool.external_write is False
    assert tool.metadata["provider_neutral"] is True
