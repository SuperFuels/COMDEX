from __future__ import annotations

from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _read_app_js() -> str:
    assert APP_JS.exists(), "desktop/mac/src/app.js must exist"
    return APP_JS.read_text(encoding="utf-8")


def test_boardroom_autonomy_ui_bridge_marker_exists() -> None:
    text = _read_app_js()

    assert "AION_WORKFLOW_CAPSULE_AUTONOMY_UI_BRIDGE_V1" in text


def test_boardroom_has_workflow_level_autonomy_controls() -> None:
    text = _read_app_js()

    assert "data-workflow-capsule-autonomy-mode" in text
    assert "data-workflow-capsule-autonomy-scope" in text
    assert "workflow" in text
    assert "Review Mode" in text
    assert "Draft Auto Mode" in text
    assert "Auto with Exceptions" in text
    assert "Manual Only" in text


def test_boardroom_has_node_level_autonomy_controls() -> None:
    text = _read_app_js()

    assert "data-workflow-capsule-node-autonomy-mode" in text
    assert "data-workflow-capsule-node-id" in text
    assert "approval_required" in text
    assert "draft_only" in text
    assert "automatic" in text
    assert "blocked" in text


def test_boardroom_autonomy_ui_explains_safe_boundaries() -> None:
    text = _read_app_js()

    assert "Create draft is not send" in text
    assert "Agents cannot self-authorise" in text
    assert "Auto mode still pauses on risk exceptions" in text
    assert "External writes stay guarded" in text


def test_boardroom_autonomy_ui_does_not_enable_live_execute() -> None:
    text = _read_app_js()

    marker = "AION_WORKFLOW_CAPSULE_AUTONOMY_UI_BRIDGE_V1"
    assert marker in text

    start = text.index(marker)
    window = text[max(0, start - 6000): start + 14000]

    assert "live_execute" not in window
    assert "send_message" not in window.lower()
    assert "gmail_live_send" not in window.lower()
