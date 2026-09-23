from __future__ import annotations

from pathlib import Path

from backend.modules.workflow_capsules.registry.workflow_glyph_registry import WorkflowGlyphRegistry
from backend.modules.workflow_capsules.habits.habit_promotion_engine import HabitPromotionEngine
from backend.modules.workflow_capsules.habits.habit_capsule_schema import HabitCapsule


def _evidence(n: int = 3, quality: float = 0.82):
    return [
        {
            "run_id": f"wf_dry_{i}",
            "run_ok": True,
            "quality": quality,
        }
        for i in range(n)
    ]


def test_habit_promotion_blocked_when_cau_denies_learning(tmp_path: Path) -> None:
    capsule = WorkflowGlyphRegistry().require("WG-001")

    engine = HabitPromotionEngine(
        habit_dir=tmp_path / "habits",
        promotion_log=tmp_path / "habit_promotion_log.jsonl",
        min_successful_runs=3,
        min_avg_quality=0.70,
    )

    result = engine.evaluate_and_promote(
        capsule=capsule,
        run_evidence=_evidence(3, 0.82),
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_cau_denied",
        },
    )

    assert result["eligible_by_evidence"] is True
    assert result["mutation_allowed"] is False
    assert result["promoted"] is False
    assert "cau_allow_learn_false" in result["blocked_reasons"]
    assert not list((tmp_path / "habits").glob("*.json"))


def test_habit_promotion_blocked_by_adr_even_when_allow_learn_true(tmp_path: Path) -> None:
    capsule = WorkflowGlyphRegistry().require("WG-001")

    engine = HabitPromotionEngine(
        habit_dir=tmp_path / "habits",
        promotion_log=tmp_path / "habit_promotion_log.jsonl",
        min_successful_runs=3,
        min_avg_quality=0.70,
    )

    result = engine.evaluate_and_promote(
        capsule=capsule,
        run_evidence=_evidence(3, 0.82),
        cau_state={
            "allow_learn": True,
            "adr_active": True,
            "deny_reason": "pytest_adr_override",
        },
    )

    assert result["eligible_by_evidence"] is True
    assert result["mutation_allowed"] is False
    assert result["promoted"] is False
    assert "adr_active" in result["blocked_reasons"]
    assert not list((tmp_path / "habits").glob("*.json"))


def test_habit_promotion_requires_enough_successful_evidence(tmp_path: Path) -> None:
    capsule = WorkflowGlyphRegistry().require("WG-001")

    engine = HabitPromotionEngine(
        habit_dir=tmp_path / "habits",
        promotion_log=tmp_path / "habit_promotion_log.jsonl",
        min_successful_runs=3,
        min_avg_quality=0.70,
    )

    result = engine.evaluate_and_promote(
        capsule=capsule,
        run_evidence=_evidence(2, 0.82),
        cau_state={
            "allow_learn": True,
            "adr_active": False,
        },
    )

    assert result["eligible_by_evidence"] is False
    assert result["mutation_allowed"] is True
    assert result["promoted"] is False
    assert "insufficient_successful_runs" in result["blocked_reasons"]


def test_habit_promotion_creates_habit_capsule_when_cau_and_evidence_pass(tmp_path: Path) -> None:
    capsule = WorkflowGlyphRegistry().require("WG-001")

    engine = HabitPromotionEngine(
        habit_dir=tmp_path / "habits",
        promotion_log=tmp_path / "habit_promotion_log.jsonl",
        min_successful_runs=3,
        min_avg_quality=0.70,
    )

    result = engine.evaluate_and_promote(
        capsule=capsule,
        run_evidence=_evidence(3, 0.82),
        cau_state={
            "allow_learn": True,
            "adr_active": False,
        },
    )

    assert result["eligible_by_evidence"] is True
    assert result["mutation_allowed"] is True
    assert result["promoted"] is True
    assert result["habit_key"] == "habit:gmail.enquiry_reply.v1"

    habit_path = Path(result["habit_path"])
    assert habit_path.exists()

    habit = HabitCapsule.load(habit_path)
    assert habit.habit_key == "habit:gmail.enquiry_reply.v1"
    assert habit.source_workflow_key == "workflow:gmail.enquiry_reply.v1"
    assert habit.evidence["successful_runs"] == 3
    assert habit.evidence["avg_quality"] == 0.82
    assert habit.resonance["sqi_score"] == 0.82
    assert habit.meta["checksum"]
