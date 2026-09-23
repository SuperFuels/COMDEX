from pathlib import Path

from backend.modules.aion.goal_engine.contracts import OutcomeEvaluationContract
from backend.modules.aion.goal_engine.evidence_sources import (
    EvidenceSourceContract,
    validate_evidence_source,
    summarize_evidence_sources,
)
from backend.modules.aion.goal_engine.outcome_scoring import (
    build_outcome_score_preview,
    summarize_outcome_evidence_state,
)


EVIDENCE_MODULE = Path("backend/modules/aion/goal_engine/evidence_sources.py")
SCORING_MODULE = Path("backend/modules/aion/goal_engine/outcome_scoring.py")


def test_evidence_source_contract_exists():
    text = EVIDENCE_MODULE.read_text()

    assert "class EvidenceSourceContract" in text
    assert "validate_evidence_source" in text
    assert "summarize_evidence_sources" in text
    assert "manual_confirmation" in text


def test_manual_confirmation_evidence_can_support_outcome_success():
    evidence = EvidenceSourceContract(
        evidence_id="ev_manual_001",
        evidence_type="manual_confirmation",
        source="boardroom",
        confidence=0.95,
        verified=True,
        provenance={"confirmed_by": "operator"},
    )

    result = validate_evidence_source(evidence)

    assert result["supports_outcome_success"] is True
    assert result["blocked_reasons"] == []


def test_unverified_evidence_does_not_support_outcome_success():
    evidence = EvidenceSourceContract(
        evidence_id="ev_manual_002",
        evidence_type="manual_confirmation",
        source="boardroom",
        confidence=0.95,
        verified=False,
    )

    result = validate_evidence_source(evidence)

    assert result["supports_outcome_success"] is False
    assert "evidence_not_verified" in result["blocked_reasons"]


def test_low_confidence_evidence_does_not_support_outcome_success():
    evidence = EvidenceSourceContract(
        evidence_id="ev_manual_003",
        evidence_type="manual_confirmation",
        source="boardroom",
        confidence=0.2,
        verified=True,
    )

    result = validate_evidence_source(evidence)

    assert result["supports_outcome_success"] is False
    assert "evidence_confidence_below_threshold" in result["blocked_reasons"]


def test_outcome_scoring_uses_evidence_source_validator():
    text = SCORING_MODULE.read_text()

    assert "from backend.modules.aion.goal_engine.evidence_sources import" in text
    assert "summarize_evidence_sources" in text
    assert "if evidence:" not in text
    assert "has_evidence = bool(evidence_source_summary.get(\"supports_outcome_success\") is True)" in text

    preview = build_outcome_score_preview(
        OutcomeEvaluationContract(
            outcome_id="outcome_001",
            goal_id="goal_001",
            run_id="run_001",
            status="success",
            quality_score=0.9,
            evidence=[
                {
                    "evidence_id": "ev_manual_004",
                    "evidence_type": "manual_confirmation",
                    "source": "boardroom",
                    "confidence": 0.95,
                    "verified": True,
                }
            ],
        )
    )

    assert preview["supports_outcome_success"] is True
    assert preview["evidence_source_summary"]["supported_evidence_count"] == 1


def test_evidence_summary_tracks_supported_and_blocked_outcomes():
    supported = build_outcome_score_preview(
        OutcomeEvaluationContract(
            outcome_id="outcome_supported",
            goal_id="goal_001",
            run_id="run_001",
            status="success",
            quality_score=0.9,
            evidence=[
                {
                    "evidence_id": "ev_supported",
                    "evidence_type": "manual_confirmation",
                    "source": "boardroom",
                    "confidence": 0.9,
                    "verified": True,
                }
            ],
        )
    )

    blocked = build_outcome_score_preview(
        OutcomeEvaluationContract(
            outcome_id="outcome_blocked",
            goal_id="goal_001",
            run_id="run_002",
            status="success",
            quality_score=0.9,
            evidence=[
                {
                    "evidence_id": "ev_blocked",
                    "evidence_type": "manual_confirmation",
                    "source": "boardroom",
                    "confidence": 0.1,
                    "verified": False,
                }
            ],
        )
    )

    summary = summarize_outcome_evidence_state([supported, blocked])
    raw_summary = summarize_evidence_sources(
        [
            {
                "evidence_id": "ev_supported",
                "evidence_type": "manual_confirmation",
                "source": "boardroom",
                "confidence": 0.9,
                "verified": True,
            },
            {
                "evidence_id": "ev_blocked",
                "evidence_type": "manual_confirmation",
                "source": "boardroom",
                "confidence": 0.1,
                "verified": False,
            },
        ]
    )

    assert summary["supported_success_count"] == 1
    assert summary["blocked_outcome_count"] == 1
    assert raw_summary["supported_evidence_count"] == 1
    assert raw_summary["blocked_evidence_count"] == 1
