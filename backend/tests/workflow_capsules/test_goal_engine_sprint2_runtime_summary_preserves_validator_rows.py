from backend.modules.aion.goal_engine.contracts import OutcomeEvaluationContract
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def test_goal_runtime_summary_preserves_evidence_validator_rows():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_evidence_rows_001",
        workflow_id="workflow_evidence_rows",
        contracts=[
            OutcomeEvaluationContract(
                outcome_id="outcome_verified_001",
                goal_id="goal_001",
                run_id="run_001",
                status="success",
                quality_score=0.9,
                evidence=[
                    {
                        "evidence_id": "ev_manual_001",
                        "evidence_type": "manual_confirmation",
                        "source": "boardroom",
                        "source_connector": "manual_confirmation",
                        "source_ref": "approval_001",
                        "confidence": 0.95,
                        "verified": True,
                        "freshness": "current",
                        "provenance": {"confirmed_by": "operator"},
                    }
                ],
            )
        ],
    )

    summary = bundle.to_dict()["goal_runtime_summary"]
    evidence_summary = summary["outcome_evidence_summary"]

    assert evidence_summary["supported_success_count"] == 1
    assert evidence_summary["blocked_outcome_count"] == 0
    assert "validations" in evidence_summary
    assert len(evidence_summary["validations"]) == 1

    validation = evidence_summary["validations"][0]
    assert validation["supports_outcome_success"] is True
    assert validation["evidence"]["evidence_id"] == "ev_manual_001"
    assert validation["evidence"]["source_connector"] == "manual_confirmation"
    assert validation["evidence"]["source_ref"] == "approval_001"
    assert validation["evidence"]["freshness"] == "current"
    assert validation["evidence"]["provenance"]["confirmed_by"] == "operator"
    assert validation["confidence"] == 0.95
    assert validation["verified"] is True


def test_goal_runtime_summary_preserves_blocked_validator_rows():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_evidence_rows_blocked_001",
        workflow_id="workflow_evidence_rows_blocked",
        contracts=[
            OutcomeEvaluationContract(
                outcome_id="outcome_blocked_001",
                goal_id="goal_001",
                run_id="run_001",
                status="success",
                quality_score=0.9,
                evidence=[
                    {
                        "evidence_id": "ev_manual_blocked_001",
                        "evidence_type": "manual_confirmation",
                        "source": "boardroom",
                        "confidence": 0.2,
                        "verified": False,
                    }
                ],
            )
        ],
    )

    summary = bundle.to_dict()["goal_runtime_summary"]
    evidence_summary = summary["outcome_evidence_summary"]

    assert evidence_summary["supported_success_count"] == 0
    assert evidence_summary["blocked_outcome_count"] == 1
    assert "validations" in evidence_summary
    assert len(evidence_summary["validations"]) == 1

    validation = evidence_summary["validations"][0]
    assert validation["supports_outcome_success"] is False
    assert "evidence_not_verified" in validation["blocked_reasons"]
    assert "evidence_confidence_below_threshold" in validation["blocked_reasons"]
