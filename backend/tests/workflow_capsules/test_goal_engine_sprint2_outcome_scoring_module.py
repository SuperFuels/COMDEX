from pathlib import Path

from backend.modules.aion.goal_engine.contracts import OutcomeEvaluationContract
from backend.modules.aion.goal_engine.outcome_scoring import (
    build_outcome_score_preview,
    summarize_outcome_evidence_state,
)


PREVIEW_BUNDLE = Path("backend/modules/aion/goal_engine/preview_bundle.py")
SCORING_MODULE = Path("backend/modules/aion/goal_engine/outcome_scoring.py")


def test_outcome_scoring_module_exists_and_exports_first_class_functions():
    text = SCORING_MODULE.read_text()

    assert "def build_outcome_score_preview(" in text
    assert "def summarize_outcome_evidence_state(" in text
    assert "outcome_success_requires_evidence" in text
    assert "Completed workflow is not successful outcome without evidence" in text


def test_outcome_scoring_blocks_success_without_evidence():
    contract = OutcomeEvaluationContract(
        outcome_id="outcome_leads_001",
        goal_id="goal_leads_001",
        run_id="run_leads_001",
        status="success",
        quality_score=0.8,
        metric_actual=3,
        metric_target=5,
        confidence=0.7,
        reason="No evidence has been attached yet.",
        evidence=[],
    )

    preview = build_outcome_score_preview(contract)

    assert preview["outcome_id"] == "outcome_leads_001"
    assert preview["goal_id"] == "goal_leads_001"
    assert preview["completed_execution_is_success"] is False
    assert preview["evidence_required"] is True
    assert preview["evidence_count"] == 0
    assert preview["success_blocked"] is True
    assert "outcome_success_requires_evidence" in preview["blocked_reasons"]


def test_outcome_scoring_allows_supported_success_when_evidence_exists():
    contract = OutcomeEvaluationContract(
        outcome_id="outcome_leads_002",
        goal_id="goal_leads_001",
        run_id="run_leads_002",
        status="success",
        quality_score=0.9,
        metric_actual=6,
        metric_target=5,
        confidence=0.85,
        evidence=[
            {
                "type": "manual_confirmation",
                "source": "boardroom",
                "confidence": 0.9,
                "freshness": "current",
            }
        ],
    )

    preview = build_outcome_score_preview(contract)

    assert preview["success_blocked"] is False
    assert preview["evidence_count"] == 1
    assert preview["metric_target_met"] is True
    assert preview["completed_execution_is_success"] is True
    assert preview["blocked_reasons"] == []


def test_outcome_evidence_summary_tracks_counts_and_blocked_reasons():
    previews = [
        build_outcome_score_preview(
            OutcomeEvaluationContract(
                outcome_id="outcome_missing_evidence",
                goal_id="goal_leads_001",
                run_id="run_001",
                status="success",
                quality_score=0.5,
                evidence=[],
            )
        ),
        build_outcome_score_preview(
            OutcomeEvaluationContract(
                outcome_id="outcome_with_evidence",
                goal_id="goal_leads_001",
                run_id="run_002",
                status="success",
                quality_score=0.9,
                evidence=[{"type": "manual_confirmation"}],
            )
        ),
    ]

    summary = summarize_outcome_evidence_state(previews)

    assert summary["outcome_count"] == 2
    assert summary["evidence_backed_outcome_count"] == 1
    assert summary["blocked_outcome_count"] == 1
    assert "outcome_success_requires_evidence" in summary["blocked_reasons"]


def test_preview_bundle_imports_outcome_scoring_module_not_inline_logic():
    text = PREVIEW_BUNDLE.read_text()

    assert "from backend.modules.aion.goal_engine.outcome_scoring import" in text
    assert "build_outcome_score_preview" in text
    assert "summarize_outcome_evidence_state" in text

    # The literal rule can appear in tests/docs and the scoring module, but
    # preview_bundle should consume the result rather than owning the rule text.
    assert "Completed workflow is not successful outcome without evidence" not in text
