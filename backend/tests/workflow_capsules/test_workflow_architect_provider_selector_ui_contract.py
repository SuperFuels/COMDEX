from __future__ import annotations

from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _read() -> str:
    return APP.read_text(encoding="utf-8")


def test_workflow_architect_provider_selector_exists() -> None:
    text = _read()

    assert "data-workflow-architect-provider-select" in text
    assert "workflowArchitectProvider" in text
    assert 'value="mock"' in text
    assert 'value="openai"' in text
    assert 'value="local_gemma"' in text


def test_workflow_architect_provider_defaults_to_mock() -> None:
    text = _read()

    assert 'workflowArchitectProvider || "mock"' in text or 'provider: "mock"' in text
    assert "mock deterministic" in text.lower() or "local deterministic" in text.lower()


def test_workflow_architect_review_request_uses_selected_provider() -> None:
    text = _read()

    assert "getWorkflowArchitectSelectedProvider" in text
    assert "syncWorkflowArchitectModalInputsToState" in text
    assert "window.__syncedArchitectInput" in text
    assert "provider" in text


def test_workflow_architect_provider_selector_has_status_copy() -> None:
    text = _read().lower()

    assert "openai" in text
    assert "local_gemma" in text
    assert "not configured" in text or "fail-closed" in text
    assert "ollama" in text or "gemma" in text


def test_workflow_architect_provider_selector_does_not_expose_live_send() -> None:
    text = _read().lower()

    forbidden = [
        "users.messages.send",
        "gmail_live_send",
        "send_message(",
        "live_execute",
    ]

    for token in forbidden:
        assert token not in text
