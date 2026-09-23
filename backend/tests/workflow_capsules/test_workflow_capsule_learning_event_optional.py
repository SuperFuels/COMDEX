from __future__ import annotations

from pathlib import Path

from backend.modules.aion_learning.runtime import AionLearningRuntime
from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
    WorkflowCapsuleRunner,
)
from backend.modules.workflow_capsules.resonance.workflow_capsule_feedback import (
    WorkflowCapsuleFeedbackEngine,
)


def test_workflow_capsule_feedback_emits_learning_event_without_capsule_mutation(tmp_path: Path) -> None:
    learning = AionLearningRuntime(data_root=str(tmp_path / "learning_data"))
    feedback = WorkflowCapsuleFeedbackEngine(
        path=tmp_path / "workflow_feedback.jsonl",
        learning_runtime=learning,
        emit_learning_events=True,
    )

    runner = WorkflowCapsuleRunner(
        feedback_engine=feedback,
        persist_feedback_capsule=False,
    )

    dry = runner.run_dry(
        "WG-001",
        inputs={"gmail_message_id": "demo-message-001"},
        available_vault_requirements=[],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_learning_event_no_capsule_mutation",
        },
        extra={"pytest": True, "stage": "learning_event_optional"},
    )

    assert dry.ok is True
    assert dry.feedback["ok"] is True
    assert dry.feedback["mutation_allowed"] is False
    assert dry.feedback["mutation_applied"] is False

    learning_event = dry.feedback["learning_event"]
    assert learning_event["ok"] is True
    assert learning_event["emitted"] is True
    assert learning_event["skill_id"] == "workflow:gmail.enquiry_reply.v1"
    assert learning_event["event_type"] == "skill_run"

    events = learning.list_events(limit=10)
    assert len(events) == 1

    event = events[0]
    assert event["schema_version"] == "aion.learning_event.v2"
    assert event["event_type"] == "skill_run"
    assert event["skill_id"] == "workflow:gmail.enquiry_reply.v1"
    assert event["skill_run_id"] == dry.run_id
    assert event["ok"] is True

    assert event["metadata"]["kind"] == "workflow_capsule_run"
    assert event["metadata"]["source"] == "workflow_capsule_feedback"
    assert event["metadata"]["dry_run"] is True
    assert event["metadata"]["blocked_count"] == 2
    assert event["metadata"]["simulated_count"] == 3
    assert event["metadata"]["total_steps"] == 5
    assert event["metadata"]["cau"]["allow_learn"] is False


def test_workflow_capsule_learning_runtime_failure_is_non_breaking(tmp_path: Path) -> None:
    class BrokenLearningRuntime:
        def record_skill_run(self, **kwargs):
            raise RuntimeError("forced learning runtime failure")

    feedback = WorkflowCapsuleFeedbackEngine(
        path=tmp_path / "workflow_feedback.jsonl",
        learning_runtime=BrokenLearningRuntime(),
        emit_learning_events=True,
    )

    runner = WorkflowCapsuleRunner(
        feedback_engine=feedback,
        persist_feedback_capsule=False,
    )

    dry = runner.run_dry(
        "WG-001",
        inputs={"gmail_message_id": "demo-message-001"},
        available_vault_requirements=[],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_learning_failure_non_breaking",
        },
        extra={"pytest": True, "stage": "learning_failure_non_breaking"},
    )

    assert dry.ok is True
    assert dry.feedback["ok"] is True
    assert dry.feedback["mutation_applied"] is False

    learning_event = dry.feedback["learning_event"]
    assert learning_event["ok"] is False
    assert learning_event["emitted"] is False
    assert learning_event["non_blocking"] is True
    assert "forced learning runtime failure" in learning_event["error"]
