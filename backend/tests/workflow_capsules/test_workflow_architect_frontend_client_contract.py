from __future__ import annotations

from pathlib import Path


CLIENT = Path("frontend/src/glyphnet/api/workflowArchitectClient.ts")


def _read() -> str:
    assert CLIENT.exists(), f"missing frontend client: {CLIENT}"
    return CLIENT.read_text(encoding="utf-8")


def test_frontend_workflow_architect_client_exists() -> None:
    text = _read()

    assert "buildWorkflowArchitectReview" in text
    assert "getWorkflowArchitectHealth" in text


def test_frontend_workflow_architect_client_calls_backend_route() -> None:
    text = _read()

    assert "/api/workflow-architect/build-review" in text
    assert "/api/workflow-architect/health" in text
    assert "POST" in text
    assert "GET" in text


def test_frontend_workflow_architect_client_defaults_to_safe_mock_provider() -> None:
    text = _read()

    assert 'provider: "mock"' in text
    assert "connected_credentials" in text
    assert "missing_credentials" in text
    assert "must_not_do" in text


def test_frontend_workflow_architect_client_does_not_expose_live_send() -> None:
    text = _read().lower()

    forbidden = [
        "users.messages.send",
        "gmail_live_send",
        "send_message(",
        "live_execute",
    ]

    for token in forbidden:
        assert token not in text
