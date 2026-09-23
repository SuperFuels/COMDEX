from backend.modules.aion.goal_engine.resume_revalidation import (
    RESUME_REVALIDATION_SCHEMA_VERSION,
    ResumeRevalidationContract,
    build_resume_revalidation_preview,
)


def test_resume_revalidation_schema_version_locked():
    assert RESUME_REVALIDATION_SCHEMA_VERSION == "aion.goal_engine.resume_revalidation.v1"


def test_resume_revalidation_passes_when_environment_is_still_valid():
    contract = ResumeRevalidationContract(
        revalidation_id="reval_001",
        run_id="run_001",
        checkpoint_id="chk_001",
        approval_still_valid=True,
        vault_ready=True,
        connectors_ready=True,
        parent_goal_still_required=True,
        external_state_changed=False,
    )

    preview = build_resume_revalidation_preview(contract)

    assert preview["schema_version"] == RESUME_REVALIDATION_SCHEMA_VERSION
    assert preview["resume_allowed"] is True
    assert preview["resume_blocked"] is False
    assert preview["blocked_reasons"] == []
    assert preview["would_resume"] is False
    assert preview["dry_run_only"] is True


def test_resume_revalidation_blocks_when_approval_is_not_valid():
    contract = ResumeRevalidationContract(
        revalidation_id="reval_approval_blocked",
        run_id="run_001",
        checkpoint_id="chk_001",
        approval_still_valid=False,
        vault_ready=True,
        connectors_ready=True,
        parent_goal_still_required=True,
        external_state_changed=False,
    )

    preview = build_resume_revalidation_preview(contract)

    assert preview["resume_allowed"] is False
    assert preview["resume_blocked"] is True
    assert "approval_not_valid" in preview["blocked_reasons"]


def test_resume_revalidation_blocks_when_vault_or_connectors_not_ready():
    contract = ResumeRevalidationContract(
        revalidation_id="reval_env_blocked",
        run_id="run_001",
        checkpoint_id="chk_001",
        approval_still_valid=True,
        vault_ready=False,
        connectors_ready=False,
        parent_goal_still_required=True,
        external_state_changed=False,
    )

    preview = build_resume_revalidation_preview(contract)

    assert preview["resume_allowed"] is False
    assert "vault_not_ready" in preview["blocked_reasons"]
    assert "connectors_not_ready" in preview["blocked_reasons"]


def test_resume_revalidation_blocks_when_parent_goal_no_longer_required():
    contract = ResumeRevalidationContract(
        revalidation_id="reval_parent_goal_blocked",
        run_id="run_001",
        checkpoint_id="chk_001",
        approval_still_valid=True,
        vault_ready=True,
        connectors_ready=True,
        parent_goal_still_required=False,
        external_state_changed=False,
    )

    preview = build_resume_revalidation_preview(contract)

    assert preview["resume_allowed"] is False
    assert "parent_goal_no_longer_required" in preview["blocked_reasons"]


def test_resume_revalidation_stops_safely_if_external_state_changed():
    contract = ResumeRevalidationContract(
        revalidation_id="reval_external_state_changed",
        run_id="run_001",
        checkpoint_id="chk_001",
        approval_still_valid=True,
        vault_ready=True,
        connectors_ready=True,
        parent_goal_still_required=True,
        external_state_changed=True,
    )

    preview = build_resume_revalidation_preview(contract)

    assert preview["resume_allowed"] is False
    assert preview["safe_stop_required"] is True
    assert "external_state_changed" in preview["blocked_reasons"]
    assert preview["suggested_next_action"] == "stop_or_replan_before_resume"


def test_resume_revalidation_never_grants_permission_or_executes():
    contract = ResumeRevalidationContract(
        revalidation_id="reval_safety",
        run_id="run_001",
        checkpoint_id="chk_001",
        approval_still_valid=True,
        vault_ready=True,
        connectors_ready=True,
        parent_goal_still_required=True,
        external_state_changed=False,
    )

    preview = build_resume_revalidation_preview(contract)

    assert preview["dry_run_only"] is True
    assert preview["would_resume"] is False
    assert preview["would_execute"] is False
    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False
