from __future__ import annotations

from pathlib import Path

from backend.modules.workflow_capsules.execution.workflow_capsule_runner import WorkflowCapsuleRunner
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import WorkflowGlyphRegistry
from backend.modules.workflow_capsules.habits.habit_promotion_engine import HabitPromotionEngine
from backend.modules.workflow_capsules.habits.habit_capsule_repository import HabitCapsuleRepository
from backend.modules.workflow_capsules.habits.habit_capsule_registry import HabitCapsuleRegistry


def _evidence(n: int = 3, quality: float = 0.82):
    return [
        {
            "run_id": f"wf_dry_{i}",
            "run_ok": True,
            "quality": quality,
        }
        for i in range(n)
    ]


def test_habit_repository_saves_and_loads_promoted_habit(tmp_path: Path) -> None:
    capsule = WorkflowGlyphRegistry().require("WG-001")

    engine = HabitPromotionEngine(
        habit_dir=tmp_path / "habits",
        promotion_log=tmp_path / "habit_promotion_log.jsonl",
    )

    result = engine.evaluate_and_promote(
        capsule=capsule,
        run_evidence=_evidence(),
        cau_state={"allow_learn": True, "adr_active": False},
    )

    assert result["promoted"] is True

    repo = HabitCapsuleRepository(habit_dir=tmp_path / "habits")
    habit = repo.require("habit:gmail.enquiry_reply.v1")

    assert habit.habit_key == "habit:gmail.enquiry_reply.v1"
    assert habit.source_workflow_key == "workflow:gmail.enquiry_reply.v1"
    assert habit.meta["checksum"]


def test_habit_registry_resolves_habit_to_source_workflow_key(tmp_path: Path) -> None:
    capsule = WorkflowGlyphRegistry().require("WG-001")

    engine = HabitPromotionEngine(
        habit_dir=tmp_path / "habits",
        promotion_log=tmp_path / "habit_promotion_log.jsonl",
    )

    result = engine.evaluate_and_promote(
        capsule=capsule,
        run_evidence=_evidence(),
        cau_state={"allow_learn": True, "adr_active": False},
    )

    assert result["promoted"] is True

    repo = HabitCapsuleRepository(habit_dir=tmp_path / "habits")
    reg = HabitCapsuleRegistry(
        repository=repo,
        registry_path=tmp_path / "habit_capsule_registry.json",
    )

    out = reg.rebuild_and_save()

    assert out["ok"] is True
    assert out["build"]["count"] == 1

    matches = reg.find("habit:gmail.enquiry_reply.v1")
    assert len(matches) == 1
    assert matches[0].reason == "exact_habit_key"
    assert matches[0].source_workflow_key == "workflow:gmail.enquiry_reply.v1"

    source = reg.resolve_source_workflow_key("habit:gmail.enquiry_reply.v1")
    assert source == "workflow:gmail.enquiry_reply.v1"

    by_tag = reg.find("gmail")
    assert by_tag
    assert by_tag[0].source_workflow_key == "workflow:gmail.enquiry_reply.v1"


def test_habit_resolves_to_source_workflow_but_runner_still_uses_normal_policy_path(tmp_path: Path) -> None:
    capsule = WorkflowGlyphRegistry().require("WG-001")

    engine = HabitPromotionEngine(
        habit_dir=tmp_path / "habits",
        promotion_log=tmp_path / "habit_promotion_log.jsonl",
    )

    result = engine.evaluate_and_promote(
        capsule=capsule,
        run_evidence=_evidence(),
        cau_state={"allow_learn": True, "adr_active": False},
    )

    assert result["promoted"] is True

    repo = HabitCapsuleRepository(habit_dir=tmp_path / "habits")
    habit_registry = HabitCapsuleRegistry(
        repository=repo,
        registry_path=tmp_path / "habit_capsule_registry.json",
    )
    habit_registry.rebuild_and_save()

    source_workflow_key = habit_registry.resolve_source_workflow_key("habit:gmail.enquiry_reply.v1")
    assert source_workflow_key == "workflow:gmail.enquiry_reply.v1"

    runner = WorkflowCapsuleRunner()

    dry = runner.run_dry(
        source_workflow_key,
        inputs={"gmail_message_id": "demo-message-001"},
        available_vault_requirements=[],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_habit_registry_execution_still_policy_gated",
        },
        extra={"pytest": True, "stage": "habit_registry_source_workflow"},
    )

    assert dry.ok is True
    assert dry.canonical_key == "workflow:gmail.enquiry_reply.v1"
    assert dry.run["approval_required"] is True
    assert dry.run["external_writes_blocked"] is True
    assert dry.approval["status"] == "pending"
    assert dry.feedback["mutation_applied"] is False
