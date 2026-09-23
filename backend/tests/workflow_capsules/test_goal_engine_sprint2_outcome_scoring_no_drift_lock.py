from pathlib import Path

from backend.modules.aion.goal_engine.contracts import OutcomeEvaluationContract
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


PREVIEW_BUNDLE = Path("backend/modules/aion/goal_engine/preview_bundle.py")
SCORING_MODULE = Path("backend/modules/aion/goal_engine/outcome_scoring.py")


def test_outcome_success_requires_evidence_rule_lives_only_in_scoring_module():
    preview_text = PREVIEW_BUNDLE.read_text()
    scoring_text = SCORING_MODULE.read_text()

    assert "outcome_success_requires_evidence" in scoring_text
    assert "outcome_success_requires_evidence" not in preview_text


def test_preview_bundle_uses_scoring_summary_blocked_reasons():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_no_drift_001",
        workflow_id="workflow_no_drift",
        contracts=[
            OutcomeEvaluationContract(
                outcome_id="outcome_no_evidence_001",
                goal_id="goal_leads_001",
                run_id="run_leads_001",
                status="success",
                quality_score=0.8,
                confidence=0.7,
                evidence=[],
            ),
        ],
    )

    summary = bundle.to_dict()["goal_runtime_summary"]

    assert "outcome_success_requires_evidence" in summary["blocked_reasons"]
    assert summary["outcome_evidence_summary"]["blocked_outcome_count"] == 1
    assert "outcome_success_requires_evidence" in summary["outcome_evidence_summary"]["blocked_reasons"]


def test_preview_bundle_does_not_duplicate_outcome_scoring_logic_literals():
    text = PREVIEW_BUNDLE.read_text()

    forbidden = [
        "success_claimed",
        "success_blocked",
        "evidence_count < 1",
        "Completed workflow is not successful outcome without evidence",
    ]

    for item in forbidden:
        assert item not in text
