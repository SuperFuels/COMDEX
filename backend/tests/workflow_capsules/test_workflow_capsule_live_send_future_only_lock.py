from __future__ import annotations

from pathlib import Path


RUNNER = Path("backend/modules/workflow_capsules/execution/workflow_capsule_runner.py")
CONNECTOR = Path("backend/modules/workflow_capsules/connectors/workflow_connector_adapter.py")
API = Path("backend/api/workflow_capsule_router.py")


def _read(path: Path) -> str:
    assert path.exists(), f"{path} must exist"
    return path.read_text(encoding="utf-8")


def test_live_send_is_future_only_and_not_default_runner_path() -> None:
    text = _read(RUNNER)

    assert "EXECUTION_MODE_CONNECTOR_READY" in text
    assert "EXECUTION_MODE_LIVE_EXECUTE" in text

    start = text.index("def resume_after_approval")
    end = text.index("def _maybe_create_approval", start)
    block = text[start:end]

    assert "external_write_ready" in block
    assert "connector_ready" in block
    assert "send_message" not in block
    assert "gmail_live_send" not in block
    assert "users.messages.send" not in block


def test_connector_live_execute_remains_guarded_not_implemented() -> None:
    text = _read(CONNECTOR)

    assert "blocked_live_env_guard" in text
    assert "blocked_live_connector_not_implemented" in text
    assert "simulated_external_write_ready" in text

    assert "send_message" not in text
    assert "users.messages.send" not in text


def test_workflow_capsule_api_defaults_to_connector_ready() -> None:
    text = _read(API)

    assert 'execution_mode: str = "connector_ready"' in text
    assert 'payload.execution_mode or "connector_ready"' in text

    start = text.index("def resume_approval")
    block = text[start:start + 2500]

    assert "resume_after_approval" in block
    assert "connector_ready" in block
    assert "live_execute" not in block


def test_no_workflow_capsule_path_exposes_send_message_endpoint() -> None:
    combined = "\n".join([
        _read(RUNNER),
        _read(CONNECTOR),
        _read(API),
    ])

    forbidden = [
        "/send-message",
        "/send_email_live",
        "users.messages.send",
        "send_message(",
    ]

    # Guard/error names are allowed because they prove live send is blocked,
    # not wired.
    assert "gmail_live_send_not_implemented" in combined

    for token in forbidden:
        assert token not in combined
