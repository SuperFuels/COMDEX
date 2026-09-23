from __future__ import annotations

from pathlib import Path

RUNNER_PATH = Path("backend/modules/workflow_capsules/execution/workflow_capsule_runner.py")


def _read_runner() -> str:
    assert RUNNER_PATH.exists(), "workflow_capsule_runner.py must exist"
    return RUNNER_PATH.read_text(encoding="utf-8")


from pathlib import Path


RUNNER = Path("backend/modules/workflow_capsules/execution/workflow_capsule_runner.py")


def _runner_text() -> str:
    assert RUNNER.exists(), "workflow_capsule_runner.py must exist"
    return RUNNER.read_text(encoding="utf-8")


def test_resume_path_imports_permission_evaluator_contracts() -> None:
    text = _runner_text()

    assert "PermissionEvaluator" in text
    assert "WorkflowPermissionPolicy" in text
    assert "PermissionEvaluationContext" in text
    assert "AgentPermissionProfile" in text


def test_resume_path_evaluates_permission_before_connector_ready() -> None:
    text = _read_runner()

    start = text.index("def resume_after_approval")
    end = text.index("def _permission_mode_from_capsule", start)
    block = text[start:end]

    assert "permission_result = self._evaluate_resume_permission" in block
    assert "self.connector_adapter.external_write_ready" in block

    evaluator_index = block.index("permission_result = self._evaluate_resume_permission")
    connector_index = block.index("self.connector_adapter.external_write_ready")
    assert evaluator_index < connector_index

def test_resume_path_delegates_live_execute_to_connector_guard() -> None:
    text = _read_runner()
    start = text.index("def resume_after_approval")
    end = text.index("def _maybe_create_approval", start)
    block = text[start:end]

    assert "execution_mode" in block
    assert "EXECUTION_MODE_CONNECTOR_READY" in block
    assert "PermissionEvaluator" in block
    assert "permission_result" in block
    assert "external_write_ready" in block

    permission_index = block.index("permission_result")
    connector_index = block.rindex("external_write_ready")
    assert permission_index < connector_index

    # Resume permission evaluates first, but live execution blocking remains
    # delegated to WorkflowConnectorAdapter.external_write_ready().
    assert "live_execute_not_allowed" not in block

def test_resume_permission_result_is_returned_for_audit() -> None:
    text = _runner_text()

    start = text.index("def resume_after_approval")
    end = text.index("def _maybe_create_approval", start)
    block = text[start:end]

    assert "permission" in block
    assert "permission_result" in block or "permission.to_dict()" in block
    assert "risk_tier" in block
    assert "decision" in block
