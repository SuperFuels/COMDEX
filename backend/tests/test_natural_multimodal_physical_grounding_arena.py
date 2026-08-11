from __future__ import annotations

import json
from pathlib import Path


RESULT = Path(__file__).resolve().parents[2] / "results/hexcore_natural_multimodal_physical_grounding_v6.json"


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_v6_uses_real_pixels_and_beats_nonsemantic_ablations() -> None:
    result = _result()
    assert result["passed"] is True
    assert result["gate"]["natural_artifacts"] == 3
    assert result["gate"]["independent_public_authorities"] == 3
    assert result["gate"]["pixel_semantic_accuracy"] >= 0.80
    assert result["gate"]["weakest_artifact_semantic_accuracy"] >= 0.75
    assert result["ablations"]["filename_only_semantic_accuracy"] == 0.0
    assert result["ablations"]["pixel_statistics_semantic_accuracy"] == 0.0


def test_active_perception_does_not_score_echoed_questions() -> None:
    result = _result()
    for case in result["cases"]:
        combined = case["combined_visual_proposal"]["active_perception"]
        assert "question" not in combined
        assert "checks" not in combined
        assert combined["affirmative_visible_evidence"]
        assert case["pixel_semantic_evaluation"]["score"] >= 0.75


def test_caption_reveal_provenance_and_physical_derivations_are_governed() -> None:
    result = _result()
    assert result["gate"]["proposal_before_caption_reveal"] is True
    assert result["gate"]["official_claim_provenance"] == 1.0
    assert result["gate"]["derived_physical_outcomes"] == 3
    assert all(case["derived_outcome_correct"] for case in result["cases"])
    for case in result["cases"]:
        assert all(
            row["epistemic_label"] == "REPORTED_BY_OFFICIAL_SOURCE"
            for row in case["official_evidence_after_commitment"]
        )


def test_cross_modal_conflicts_and_measurement_ood_fail_closed() -> None:
    result = _result()
    assert result["gate"]["cross_modal_conflicts_detected"] == 3
    assert result["gate"]["unsupported_pre_reveal_claims"] == 0
    assert result["gate"]["unsafe_knowledge_commitments"] == 0
    assert all(
        case["cross_modal_contradiction"]["epistemic_label"] == "DISPUTED_BY_PIXEL_EVIDENCE"
        for case in result["cases"]
    )
    assert result["ood"]["abstained"] is True
    assert result["ood"]["accepted_physical_claim"] is False


def test_v6_promotion_and_restart_retention() -> None:
    result = _result()
    decision = result["promotion"]["decision"]
    assert decision["promoted"] is True or decision["champion_id"] == result["promotion"]["candidate"]["procedure_id"]
    assert result["restart"] == {
        "champion_retained": True,
        "cohort_retained": True,
        "relearning_artifacts": 0,
    }
