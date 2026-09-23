from backend.modules.connectors.dry_run_renderer import render_connector_dry_run


def test_gmail_read_actions_render_safe_previews() -> None:
    for action_id in [
        "gmail.watch_emails",
        "gmail.search_emails",
        "gmail.get_email",
        "gmail.list_attachments",
    ]:
        result = render_connector_dry_run(action_id)

        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["status"] == "previewed"
        assert result["risk_tier"] == "low"
        assert result["permission_mode"] == "read"
        assert "Would" in result["message"]


def test_gmail_create_draft_waits_for_approval_and_does_not_send() -> None:
    result = render_connector_dry_run("gmail.create_draft", approved=False)

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["status"] == "waiting_for_approval"
    assert result["risk_tier"] == "medium"
    assert result["permission_mode"] == "draft_write"
    assert result["requires_approval"] is True
    assert result["external_write"] is True
    assert result["live_execution_enabled"] is False
    assert result["message"] == "Would create a Gmail draft after approval. No email is sent."


def test_gmail_create_draft_after_approval_is_connector_ready_only() -> None:
    result = render_connector_dry_run("gmail.create_draft", approved=True)

    assert result["ok"] is True
    assert result["status"] == "approved_connector_ready"
    assert result["message"] == "Approved and ready to create a Gmail draft. No email will be sent automatically."
    assert result["live_execution_enabled"] is False


def test_gmail_live_send_family_is_blocked_future_only() -> None:
    expected = {
        "gmail.send_email": "Blocked. Live email sending is not enabled.",
        "gmail.reply_email": "Blocked. Live email replies are not enabled.",
        "gmail.send_draft": "Blocked. Sending drafts is not enabled.",
    }

    for action_id, message in expected.items():
        result = render_connector_dry_run(action_id, approved=True, live_execution_requested=True)

        assert result["ok"] is False
        assert result["dry_run"] is True
        assert result["status"] == "blocked_future_only"
        assert result["risk_tier"] == "high"
        assert result["permission_mode"] == "live_write_blocked"
        assert result["live_execution_enabled"] is False
        assert result["message"] == message


def test_gmail_api_call_is_blocked() -> None:
    result = render_connector_dry_run("gmail.api_call", approved=True)

    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["risk_tier"] == "blocked"
    assert result["permission_mode"] == "blocked"
    assert result["message"] == "Blocked. Custom Gmail API calls require explicit allowlist approval."


def test_unknown_connector_action_is_blocked() -> None:
    result = render_connector_dry_run("fake.crm.destroy_everything")

    assert result["ok"] is False
    assert result["status"] == "blocked_unknown_action"
    assert result["risk_tier"] == "blocked"
    assert result["permission_mode"] == "blocked"
    assert result["message"] == "Blocked. This connector action is not registered in AION."


def test_bridge_actions_are_dry_run_first() -> None:
    for action_id in ["http.request", "webhook.receive", "automation_bridge.trigger_scenario"]:
        result = render_connector_dry_run(action_id)

        assert result["dry_run"] is True
        assert result["live_execution_enabled"] is False
        assert "live" in result["message"].lower() or "would" in result["message"].lower()


def test_explicit_bridge_actions_are_blocked_future_only_and_permission_gated() -> None:
    expected = {
        "make.trigger_scenario": "Make.com scenario",
        "zapier.trigger_zap": "Zapier Zap",
        "n8n.trigger_workflow": "n8n workflow",
    }

    for action_id, phrase in expected.items():
        result = render_connector_dry_run(action_id, approved=True, live_execution_requested=True)

        assert result["ok"] is False
        assert result["dry_run"] is True
        assert result["status"] == "blocked_future_only"
        assert result["risk_tier"] == "high"
        assert result["permission_mode"] == "live_write_blocked"
        assert result["requires_approval"] is True
        assert result["external_write"] is True
        assert result["live_execution_enabled"] is False
        assert phrase in result["message"]
        assert "Live bridge execution is not enabled." in result["message"]
