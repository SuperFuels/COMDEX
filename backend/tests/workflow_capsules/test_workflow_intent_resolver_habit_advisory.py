from pathlib import Path

from backend.modules.workflow_capsules.registry.workflow_glyph_registry import WorkflowGlyphRegistry
from backend.modules.workflow_capsules.orchestration.workflow_intent_resolver import WorkflowIntentResolver
from backend.modules.workflow_capsules.habits.habit_promotion_engine import HabitPromotionEngine
from backend.modules.workflow_capsules.habits.habit_capsule_repository import HabitCapsuleRepository
from backend.modules.workflow_capsules.habits.habit_capsule_registry import HabitCapsuleRegistry


def _evidence():
    return [
        {"run_id": "wf_dry_1", "run_ok": True, "quality": 0.87},
        {"run_id": "wf_dry_2", "run_ok": True, "quality": 0.87},
        {"run_id": "wf_dry_3", "run_ok": True, "quality": 0.87},
    ]


def test_intent_resolver_uses_habit_registry_advisory_resolution(tmp_path: Path) -> None:
    capsule = WorkflowGlyphRegistry().require("WG-001")

    habit_dir = tmp_path / "habits"
    habit_registry_path = tmp_path / "habit_capsule_registry.json"

    promotion = HabitPromotionEngine(
        habit_dir=habit_dir,
        promotion_log=tmp_path / "habit_promotion_log.jsonl",
    ).evaluate_and_promote(
        capsule=capsule,
        run_evidence=_evidence(),
        cau_state={"allow_learn": True, "adr_active": False},
    )

    assert promotion["promoted"] is True

    habit_repo = HabitCapsuleRepository(habit_dir=habit_dir)
    habit_registry = HabitCapsuleRegistry(
        repository=habit_repo,
        registry_path=habit_registry_path,
    )

    resolver = WorkflowIntentResolver(
        registry=WorkflowGlyphRegistry(),
        habit_registry=habit_registry,
    )

    result = resolver.resolve("habit:gmail.enquiry_reply.v1")

    assert result.ok is True
    assert result.matched is True
    assert result.canonical_key == "workflow:gmail.enquiry_reply.v1"
    assert result.reason.startswith("habit_advisory_match:")
