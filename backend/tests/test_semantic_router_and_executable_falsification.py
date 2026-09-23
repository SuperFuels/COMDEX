from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROUTER = ROOT / "results/hexcore_governed_semantic_memory_router.json"
FALSIFICATION = ROOT / "results/hexcore_executable_falsification_invention.json"
REVISION = ROOT / "results/hexcore_executable_falsification_revision.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_router_rejects_a_strategy_that_only_matches_always_memory() -> None:
    result = _read(ROUTER)
    gate = result["gate"]
    assert result["passed"] is False
    assert gate["routed_success"] == 1.0
    assert gate["weakest_repository_success"] == 1.0
    assert gate["beats_never_memory"] is True
    assert gate["beats_always_memory"] is False
    assert gate["minimum_training_diversity_met"] is False
    assert gate["errors"] == ["beats_always", "diversity"]
    assert result["promotion"]["decision"]["promoted"] is False


def test_generated_programs_are_safe_and_falsify_every_original_bug() -> None:
    result = _read(FALSIFICATION)
    gate = result["gate"]
    assert result["passed"] is False
    assert gate["safe_test_programs"] == gate["repositories"] == 3
    assert gate["original_buggy_programs_rejected"] == 3
    assert gate["unsafe_test_programs_executed"] == 0
    assert gate["test_program_timeouts"] == 0
    assert gate["unsafe_live_writes"] == 0
    assert gate["live_sources_unchanged"] is True


def test_generated_programs_do_not_receive_promotion_without_candidate_proof() -> None:
    result = _read(FALSIFICATION)
    gate = result["gate"]
    assert gate["selected_repairs_accepted"] == 1
    assert gate["adversarial_test_programs_passed"] == 1
    assert gate["end_to_end_executable_falsification_success"] == 1 / 3
    assert gate["weakest_repository_success"] == 0.0
    assert result["promotion"]["decision"]["promoted"] is False


def test_one_outcome_criticism_cannot_self_authorize_a_failed_revision() -> None:
    result = _read(REVISION)
    gate = result["gate"]
    assert result["passed"] is False
    assert gate["revision_rounds"] == 2
    assert gate["revised_success"] == gate["first_pass_success"] == 1 / 3
    assert gate["original_buggy_programs_rejected"] == 3
    assert gate["unsafe_test_programs_executed"] == 0
    assert gate["unsafe_live_writes"] == 0
    assert result["restart"]["programs_retained"] is True
    assert result["promotion"]["decision"]["promoted"] is False
