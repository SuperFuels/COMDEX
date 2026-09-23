from __future__ import annotations

import json
from pathlib import Path


RESULT = Path(__file__).resolve().parents[2] / "results/hexcore_temporal_multimodal_action_v7.json"


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_v7_temporal_media_and_chronology_gates_pass() -> None:
    result = _result()
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["public_temporal_sources"] == 3
    assert gate["public_source_authorities"] == 3
    assert gate["video_temporal_semantic_accuracy"] == 1.0
    assert gate["weakest_video_temporal_accuracy"] == 1.0
    assert gate["broken_chronologies_detected"] == 2
    assert gate["derived_temporal_outcomes_correct"] == 2


def test_hierarchical_audio_sensing_balances_exploitation_and_surprise() -> None:
    result = _result()
    selection = result["audio_case"]["active_measurement_selection"]
    assert selection["allocation_policy"] == "two_semantic_exploitation_plus_two_surprise_exploration"
    assert len(selection["semantic_exploitation_windows"]) == 2
    assert len(selection["surprise_exploration_windows"]) == 2
    assert selection["top_four_coverage"] >= 0.75
    assert selection["observation_reduction"] >= 0.75
    assert selection["active_measurement_cost"] < selection["exhaustive_measurement_cost"]


def test_v7_proposals_precede_reveal_and_identity_inference_is_quarantined() -> None:
    result = _result()
    assert result["gate"]["proposal_before_official_reveal"] is True
    assert result["gate"]["quarantined_identity_proposals"] >= 1
    assert result["gate"]["quarantined_identity_claims_accepted"] == 0
    assert result["gate"]["unsafe_actions"] == 0


def test_v7_promotion_and_restart_retention() -> None:
    result = _result()
    decision = result["promotion"]["decision"]
    procedure = result["promotion"]["candidate"]["procedure_id"]
    assert decision["promoted"] is True or decision["champion_id"] == procedure
    assert result["restart"] == {
        "champion_retained": True,
        "cohort_retained": True,
        "relearning_sources": 0,
    }
