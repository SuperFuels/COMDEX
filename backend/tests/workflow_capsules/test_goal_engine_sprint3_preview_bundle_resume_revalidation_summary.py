from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle
from backend.modules.aion.goal_engine.resume_revalidation import ResumeRevalidationContract


def test_preview_bundle_exposes_resume_revalidation_summary():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_resume_bundle_001",
        workflow_id="workflow_resume_bundle",
        contracts=[
            ResumeRevalidationContract(
                revalidation_id="reval_001",
                run_id="run_resume_bundle_001",
                checkpoint_id="chk_001",
                approval_still_valid=True,
                vault_ready=True,
                connectors_ready=True,
                parent_goal_still_required=True,
                external_state_changed=False,
            ),
        ],
    )

    payload = bundle.to_dict()

    assert "resume_revalidation_summary" in payload
    summary = payload["resume_revalidation_summary"]

    assert summary["trace_type"] == "resume_revalidation_summary"
    assert summary["revalidation_count"] == 1
    assert summary["resume_allowed_count"] == 1
    assert summary["resume_blocked_count"] == 0
    assert summary["safe_stop_required_count"] == 0
    assert summary["dry_run_only"] is True
    assert summary["would_resume"] is False


def test_preview_bundle_resume_revalidation_summary_tracks_blocked_reasons():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_resume_blocked_001",
        workflow_id="workflow_resume_blocked",
        contracts=[
            ResumeRevalidationContract(
                revalidation_id="reval_blocked_001",
                run_id="run_resume_blocked_001",
                checkpoint_id="chk_001",
                approval_still_valid=False,
                vault_ready=False,
                connectors_ready=False,
                parent_goal_still_required=False,
                external_state_changed=False,
            ),
        ],
    )

    summary = bundle.to_dict()["resume_revalidation_summary"]

    assert summary["resume_allowed_count"] == 0
    assert summary["resume_blocked_count"] == 1
    assert "approval_not_valid" in summary["blocked_reasons"]
    assert "vault_not_ready" in summary["blocked_reasons"]
    assert "connectors_not_ready" in summary["blocked_reasons"]
    assert "parent_goal_no_longer_required" in summary["blocked_reasons"]


def test_preview_bundle_resume_revalidation_summary_tracks_safe_stop():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_resume_safe_stop_001",
        workflow_id="workflow_resume_safe_stop",
        contracts=[
            ResumeRevalidationContract(
                revalidation_id="reval_safe_stop_001",
                run_id="run_resume_safe_stop_001",
                checkpoint_id="chk_001",
                approval_still_valid=True,
                vault_ready=True,
                connectors_ready=True,
                parent_goal_still_required=True,
                external_state_changed=True,
            ),
        ],
    )

    summary = bundle.to_dict()["resume_revalidation_summary"]

    assert summary["resume_allowed_count"] == 0
    assert summary["resume_blocked_count"] == 1
    assert summary["safe_stop_required_count"] == 1
    assert "external_state_changed" in summary["blocked_reasons"]
    assert summary["revalidation_previews"][0]["suggested_next_action"] == "stop_or_replan_before_resume"
