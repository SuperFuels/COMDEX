from backend.modules.connectors.connector_registry import get_connector_registry


def test_connector_registry_contains_gmail_reference_connector():
    registry = get_connector_registry()

    gmail = registry.get_connector("gmail")

    assert gmail is not None
    assert gmail.native_status == "reference_connector"

    action_ids = {action.action_id for action in gmail.actions}
    assert "gmail.watch_emails" in action_ids
    assert "gmail.create_draft" in action_ids
    assert "gmail.send_email" in action_ids
    assert "gmail.api_call" in action_ids


def test_gmail_create_draft_is_approval_gated_but_not_live_send():
    registry = get_connector_registry()

    action = registry.get_action("gmail.create_draft")

    assert action is not None
    assert action.risk_tier == "medium"
    assert action.permission_mode == "draft_write"
    assert action.requires_approval is True
    assert action.external_write is True
    assert action.live_execution_enabled is False


def test_gmail_live_send_actions_are_blocked_until_future_phase():
    registry = get_connector_registry()

    for action_id in ["gmail.send_email", "gmail.reply_email", "gmail.send_draft"]:
        action = registry.get_action(action_id)
        assert action is not None
        assert action.risk_tier == "high"
        assert action.permission_mode == "live_write_blocked"
        assert action.requires_approval is True
        assert action.external_write is True
        assert action.live_execution_enabled is False


def test_gmail_custom_api_call_is_blocked():
    registry = get_connector_registry()

    action = registry.get_action("gmail.api_call")

    assert action is not None
    assert action.risk_tier == "blocked"
    assert action.permission_mode == "blocked"
    assert action.live_execution_enabled is False


def test_long_tail_connector_strategy_exists():
    registry = get_connector_registry()

    assert registry.get_connector("http") is not None
    assert registry.get_connector("automation_bridge") is not None
    assert registry.get_action("http.request") is not None
    assert registry.get_action("automation_bridge.trigger_scenario") is not None

def test_connector_actions_expose_universal_runtime_schema():
    """
    Every connector action must expose the shared Aion runtime contract.

    This is the foundation that lets Aion scale beyond native Gmail:
    - the architect can reason about actions generically
    - the canvas can render actions generically
    - dry-run can explain actions generically
    - permission/risk checks can apply consistently
    """
    from backend.modules.connectors.connector_registry import ConnectorRegistry

    registry = ConnectorRegistry()
    actions = registry.list_actions()

    assert actions, "connector registry should expose at least one action"

    allowed_risk_tiers = {"low", "medium", "high", "blocked"}
    allowed_permission_modes = {
        "read",
        "draft_write",
        "approval_write",
        "live_write_blocked",
        "blocked",
    }

    for action in actions:
        payload = action.to_dict()

        assert payload["action_id"]
        assert payload["connector_id"]
        assert payload["label"]
        assert payload["description"]
        assert payload["risk_tier"] in allowed_risk_tiers
        assert payload["permission_mode"] in allowed_permission_modes

        assert "external_write" in payload
        assert isinstance(payload["external_write"], bool)

        assert "requires_approval" in payload
        assert isinstance(payload["requires_approval"], bool)

        assert "live_execution_enabled" in payload
        assert isinstance(payload["live_execution_enabled"], bool)

        if payload["external_write"]:
            assert payload["permission_mode"] in {
                "draft_write",
                "approval_write",
                "live_write_blocked",
                "blocked",
            }

        if payload["risk_tier"] in {"high", "blocked"}:
            assert payload["live_execution_enabled"] is False


def test_gmail_send_family_is_visible_but_live_blocked():
    """
    Gmail send/reply/send-draft should be visible in the catalogue,
    but not executable live yet.
    """
    from backend.modules.connectors.connector_registry import ConnectorRegistry

    registry = ConnectorRegistry()

    blocked_send_actions = [
        "gmail.send_email",
        "gmail.reply_email",
        "gmail.send_draft",
    ]

    for action_id in blocked_send_actions:
        action = registry.get_action(action_id)
        assert action is not None, f"{action_id} should exist as a locked capability"

        payload = action.to_dict()
        assert payload["risk_tier"] == "high"
        assert payload["permission_mode"] == "live_write_blocked"
        assert payload["external_write"] is True
        assert payload["requires_approval"] is True
        assert payload["live_execution_enabled"] is False


def test_gmail_create_draft_is_first_allowed_real_write_candidate():
    """
    Gmail create_draft is the first write we can safely unlock later.

    It is still approval-gated and not live-executed by default,
    but it is not in the blocked send family.
    """
    from backend.modules.connectors.connector_registry import ConnectorRegistry

    registry = ConnectorRegistry()
    action = registry.get_action("gmail.create_draft")

    assert action is not None

    payload = action.to_dict()
    assert payload["risk_tier"] == "medium"
    assert payload["permission_mode"] == "draft_write"
    assert payload["external_write"] is True
    assert payload["requires_approval"] is True


def test_explicit_bridge_connectors_are_split_and_permission_gated():
    registry = get_connector_registry()

    expected = {
        "make": "make.trigger_scenario",
        "zapier": "zapier.trigger_zap",
        "n8n": "n8n.trigger_workflow",
    }

    for connector_id, action_id in expected.items():
        connector = registry.get_connector(connector_id)
        assert connector is not None
        assert connector.category == "bridge"
        assert connector.native_status == "bridge_connector"

        action = registry.get_action(action_id)
        assert action is not None
        assert action.connector_id == connector_id
        assert action.risk_tier == "high"
        assert action.permission_mode == "live_write_blocked"
        assert action.requires_approval is True
        assert action.external_write is True
        assert action.live_execution_enabled is False
        assert action.dry_run_supported is True
        assert action.requires_vault == [f"vault.{connector_id}.credentials"]
        assert action.metadata["permission_gated"] is True
        assert action.metadata["dry_run_first"] is True


def test_legacy_automation_bridge_remains_but_points_to_explicit_bridge_actions():
    registry = get_connector_registry()

    legacy = registry.get_connector("automation_bridge")
    action = registry.get_action("automation_bridge.trigger_scenario")

    assert legacy is not None
    assert legacy.native_status == "legacy_alias"
    assert action is not None
    assert action.permission_mode == "live_write_blocked"
    assert action.live_execution_enabled is False
    assert action.metadata["legacy_alias"] is True
    assert action.metadata["prefer_actions"] == [
        "make.trigger_scenario",
        "zapier.trigger_zap",
        "n8n.trigger_workflow",
    ]
