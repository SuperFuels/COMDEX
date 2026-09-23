from __future__ import annotations

from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _read_app_js() -> str:
    assert APP_JS.exists(), "desktop/mac/src/app.js must exist"
    return APP_JS.read_text(encoding="utf-8")


def test_boardroom_workflow_capsule_approval_controls_exist() -> None:
    text = _read_app_js()

    assert "data-workflow-capsule-approval-action" in text
    assert "data-workflow-capsule-approval-id" in text
    assert "Approve workflow capsule" in text
    assert "Reject workflow capsule" in text


def test_boardroom_workflow_capsule_approval_displays_permission_metadata() -> None:
    text = _read_app_js()

    assert "permission_decision" in text
    assert "risk_tier" in text
    assert "vault_requirements" in text
    assert "external_write_step_id" in text
    assert "Dry-run preview" in text


def test_boardroom_workflow_capsule_approval_uses_guarded_connector_ready_resume() -> None:
    text = _read_app_js()

    assert "/api/workflow-capsules/approvals/" in text
    assert "/approve" in text
    assert "/reject" in text
    assert "/resume" in text
    assert 'execution_mode: "connector_ready"' in text or '"execution_mode":"connector_ready"' in text


def test_boardroom_workflow_capsule_approval_never_uses_live_execute() -> None:
    text = _read_app_js()

    marker = "AION_WORKFLOW_CAPSULE_BOARDROOM_APPROVAL_BRIDGE_V1"
    assert marker in text

    start = text.index(marker)
    window = text[max(0, start - 6000): start + 12000]

    assert "live_execute" not in window
    assert "gmail_live_send" not in window.lower()
    assert "send_message" not in window.lower()
