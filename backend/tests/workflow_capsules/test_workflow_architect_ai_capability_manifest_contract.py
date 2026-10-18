from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    assert APP_JS.exists(), "desktop/mac/src/app.js not found"
    return APP_JS.read_text(encoding="utf-8")


def test_ai_architect_exposes_capability_manifest_for_describe_mode() -> None:
    text = _read()

    assert "function getAionArchitectCapabilityManifest()" in text
    assert "advanced_capabilities" in text
    assert "architect_prompt_context" in text
    assert "syncAionArchitectCapabilityManifestToInput" in text


def test_ai_architect_manifest_lists_workflow_tools() -> None:
    text = _read()

    for token in [
        "filters",
        "variables",
        "text_tools",
        "dates",
        "lists",
        "json",
        "conditions",
        "connector_actions",
    ]:
        assert token in text


def test_ai_architect_manifest_includes_core_connector_actions() -> None:
    text = _read()

    for action_id in [
        "gmail.watch_emails",
        "gmail.search_emails",
        "gmail.get_email",
        "gmail.create_draft",
        "hubspot.create_or_update_contact",
        "mailchimp.add_subscriber",
        "aion.extract_fields",
        "aion.classify_lead",
        "aion.human_approval",
    ]:
        assert action_id in text


def test_ai_architect_manifest_keeps_safety_contract() -> None:
    text = _read()

    assert "dry_run_only" in text
    assert "approval_gated" in text
    assert "valid_review_required" in text
    assert "requires_valid_dry_run_plus_confirmation" in text


def test_ai_architect_build_review_syncs_manifest_before_generation() -> None:
    text = _read()

    assert "syncAionArchitectCapabilityManifestToInput();" in text
    assert "...getAionArchitectBuildReviewPayloadExtras()" in text
