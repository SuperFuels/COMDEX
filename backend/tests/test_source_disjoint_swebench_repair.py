from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_source_disjoint_swebench_pilot_is_governed_and_persistent():
    result = json.loads(
        (
            ROOT / "results/hexcore_source_disjoint_swebench_repair.json"
        ).read_text(encoding="utf-8")
    )
    state = json.loads(
        (
            ROOT
            / "backend/modules/hexcore/data/"
            "source_disjoint_swebench_repair_state.json"
        ).read_text(encoding="utf-8")
    )

    assert result["passed"] is True
    assert result["gate"]["source_disjoint_repositories"] == 3
    assert result["gate"]["fault_localization_accuracy"] == 1.0
    assert result["gate"]["repair_success"] == 1.0
    assert result["gate"]["weakest_repository_success"] == 1.0
    assert result["gate"]["wrong_candidates_rejected"] == 6
    assert result["gate"]["held_out_operator_transfer"] is True
    assert result["gate"]["transfer_attempt_reduction"] > 0.66
    assert result["gate"]["human_patch_blind_during_search"] is True
    assert result["gate"]["hidden_behavioral_verification"] == 1.0
    assert result["gate"]["unsafe_live_writes"] == 0
    assert result["restart"]["relearning_failures"] == 0
    assert result["restart"]["curriculum_retained"] is True
    assert result["curriculum"]["selected_from_observed_outcomes"] is True
    assert (
        result["curriculum"]["next_objective"]
        == "replace_task_family_candidate_menus_with_open_patch_generation"
    )
    assert (
        state["champions"]["source_disjoint_public_repository_repair"]
        == "procedure_source_disjoint_swebench_repair_2f2e871e3879"
    )
    assert len(state["source_disjoint_patch_library"]) == 3
    assert state["source_disjoint_repair_curricula"]
