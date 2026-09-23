from backend.modules.connectors.connector_registry import get_connector_registry


def test_native_connector_strategy_prefers_high_value_apps_only():
    """
    AION should not chase thousands of native integrations.

    Native connectors are reserved for high-value apps that need deep,
    safe, permission-aware behaviour. Long-tail apps should go through
    Make.com, Zapier, n8n, HTTP, or webhook bridges.
    """
    registry = get_connector_registry()

    native_candidates = {
        "gmail",
        "google_calendar",
        "google_sheets",
        "hubspot",
        "mailchimp",
        "stripe",
        "revolut",
        "xero",
        "wordpress",
        "facebook",
    }

    bridge_connectors = {
        "make",
        "zapier",
        "n8n",
        "http",
        "automation_bridge",
    }

    # Current implemented connector baseline.
    assert registry.get_connector("gmail") is not None

    # Long-tail bridge baseline.
    for connector_id in bridge_connectors:
        assert registry.get_connector(connector_id) is not None

    # Strategy contract: do not require all candidate native connectors now.
    # They are a roadmap list, not a build obligation.
    assert "gmail" in native_candidates
    assert "xero" in native_candidates
    assert "hubspot" in native_candidates
    assert "facebook" in native_candidates

    # Bridge actions must exist for long-tail execution.
    assert registry.get_action("make.trigger_scenario") is not None
    assert registry.get_action("zapier.trigger_zap") is not None
    assert registry.get_action("n8n.trigger_workflow") is not None
    assert registry.get_action("http.request") is not None


def test_bridge_connectors_are_the_long_tail_strategy():
    registry = get_connector_registry()

    for action_id in [
        "make.trigger_scenario",
        "zapier.trigger_zap",
        "n8n.trigger_workflow",
        "http.request",
        "webhook.receive",
    ]:
        action = registry.get_action(action_id)
        assert action is not None
        assert action.live_execution_enabled is False

        if action.external_write:
            assert action.requires_approval is True
            assert action.permission_mode in {"live_write_blocked", "approval_write", "blocked"}
