from backend.services.aion_mission_mode.mission_failure_recovery import (
    classify_failure_state,
    create_failure_receipt,
    create_recovery_summary,
    preserve_partial_outputs,
    propose_revised_safe_plan,
    recover_failed_mission,
)


def test_phase20q_classifies_blocked_for_safety() -> None:
    assert classify_failure_state(blocked_for_safety=True) == "blocked_for_safety"


def test_phase20q_classifies_partial_success() -> None:
    assert classify_failure_state(partial_outputs_available=True, recoverable=True) == "partial_success"


def test_phase20q_classifies_failed_recoverable() -> None:
    assert classify_failure_state(recoverable=True) == "failed_recoverable"


def test_phase20q_classifies_failed_final() -> None:
    assert classify_failure_state(recoverable=False) == "failed_final"


def test_phase20q_preserves_partial_outputs() -> None:
    result = preserve_partial_outputs(
        mission_id="mission_001",
        mission_run_id="run_001",
        outputs=[
            {
                "output_id": "offer_001",
                "step_id": "draft_offer",
                "artifact_type": "campaign_offer",
                "business_container_path": "business_containers/home_fixed/campaigns/offer_001.json",
            }
        ],
    )

    assert result["preserved_count"] == 1
    assert result["preserved_outputs"][0]["output_hash"].startswith("sha256:")
    assert result["partial_outputs_hash"].startswith("sha256:")


def test_phase20q_failure_receipt_preserves_trace_proof_and_receipts() -> None:
    receipt = create_failure_receipt(
        mission_id="mission_001",
        mission_run_id="run_001",
        failure_state="blocked_for_safety",
        failure_reason="aggregate_external_message_path",
        stopped_step_id="send_step",
        trace_hash="sha256:trace",
        proof_hash="sha256:proof",
        partial_output_hashes=["sha256:output"],
        receipt_hashes=["sha256:receipt"],
        blocked_actions=["send_customer_message"],
    )

    assert receipt["trace_hash"] == "sha256:trace"
    assert receipt["proof_hash"] == "sha256:proof"
    assert receipt["partial_output_hashes"] == ["sha256:output"]
    assert receipt["receipt_hashes"] == ["sha256:receipt"]
    assert receipt["failure_receipt_hash"].startswith("sha256:")


def test_phase20q_recovery_summary_user_message_explains_stop() -> None:
    preserved = preserve_partial_outputs(
        mission_id="mission_001",
        mission_run_id="run_001",
        outputs=[],
    )
    receipt = create_failure_receipt(
        mission_id="mission_001",
        mission_run_id="run_001",
        failure_state="blocked_for_safety",
        failure_reason="unsafe aggregate sequence",
        stopped_step_id="step_003",
        trace_hash="sha256:trace",
        proof_hash="sha256:proof",
        partial_output_hashes=[],
        receipt_hashes=[],
        blocked_actions=["send_customer_message"],
    )

    summary = create_recovery_summary(
        mission_id="mission_001",
        mission_run_id="run_001",
        failure_receipt=receipt,
        preserved_outputs=preserved,
    )

    assert "stopped" in summary["user_message"].lower()
    assert summary["summary_hash"].startswith("sha256:")


def test_phase20q_revised_plan_converts_blocked_actions_to_checkpoint() -> None:
    revised = propose_revised_safe_plan(
        mission_id="mission_001",
        mission_run_id="run_001",
        original_steps=[
            {"step_id": "draft", "action_type": "draft_offer", "lane": "creation"},
            {"step_id": "send", "action_type": "send_customer_message", "lane": "external_action"},
        ],
        blocked_actions=["send_customer_message"],
    )

    send_step = [s for s in revised["revised_steps"] if s["step_id"] == "send"][0]

    assert send_step["decision"] == "checkpoint_required"
    assert send_step["requires_human_review"] is True
    assert send_step["live_execution_allowed"] is False
    assert revised["live_side_effects_enabled"] is False


def test_phase20q_revised_plan_keeps_safe_steps_safe() -> None:
    revised = propose_revised_safe_plan(
        mission_id="mission_001",
        mission_run_id="run_001",
        original_steps=[
            {"step_id": "draft", "action_type": "draft_offer", "lane": "creation"},
        ],
        blocked_actions=[],
    )

    assert revised["revised_steps"][0]["decision"] == "safe_autonomous"
    assert revised["revised_steps"][0]["live_execution_allowed"] is False


def test_phase20q_full_recovery_preserves_outputs_and_generates_revised_plan() -> None:
    result = recover_failed_mission(
        mission_id="mission_001",
        mission_run_id="run_001",
        failure_reason="aggregate external messaging path",
        stopped_step_id="send",
        trace_hash="sha256:trace",
        proof_hash="sha256:proof",
        outputs=[
            {
                "output_id": "advert_001",
                "step_id": "draft_advert",
                "artifact_type": "advert_draft",
                "business_container_path": "business_containers/home_fixed/campaigns/advert_001.json",
            }
        ],
        receipt_hashes=["sha256:receipt"],
        blocked_actions=["send_customer_message"],
        original_steps=[
            {"step_id": "draft_advert", "action_type": "draft_facebook_advert", "lane": "creation"},
            {"step_id": "send", "action_type": "send_customer_message", "lane": "external_action"},
        ],
        blocked_for_safety=True,
    )

    assert result["failure_state"] == "blocked_for_safety"
    assert result["preserved_outputs"]["preserved_count"] == 1
    assert result["failure_receipt"]["trace_hash"] == "sha256:trace"
    assert result["failure_receipt"]["proof_hash"] == "sha256:proof"
    assert result["revised_plan"]["live_side_effects_enabled"] is False
    assert result["recovery_hash"].startswith("sha256:")


def test_phase20q_recovery_hash_is_deterministic() -> None:
    kwargs = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        failure_reason="aggregate external messaging path",
        stopped_step_id="send",
        trace_hash="sha256:trace",
        proof_hash="sha256:proof",
        outputs=[],
        receipt_hashes=[],
        blocked_actions=["send_customer_message"],
        original_steps=[
            {"step_id": "send", "action_type": "send_customer_message", "lane": "external_action"},
        ],
        blocked_for_safety=True,
    )

    first = recover_failed_mission(**kwargs)
    second = recover_failed_mission(**kwargs)

    assert first["recovery_hash"] == second["recovery_hash"]


def test_phase20q1_atomic_recovery_transition_blocks_for_safety() -> None:
    from backend.services.aion_mission_mode.mission_failure_recovery import atomic_recovery_transition

    transition = atomic_recovery_transition(
        current_state="running_autonomous_steps",
        error_type="aggregate_forbidden_outcome",
        safety_violation_found=True,
        partial_outputs_available=True,
    )

    assert transition["target_state"] == "blocked_for_safety"
    assert transition["execution_threads_frozen"] is True
    assert transition["active_vfs_handle_suspended"] is True
    assert transition["snapshot_buffer_required"] is True
    assert transition["process_permissions_dropped"] is True
    assert transition["transition_hash"].startswith("sha256:")


def test_phase20q1_atomic_recovery_transition_partial_success() -> None:
    from backend.services.aion_mission_mode.mission_failure_recovery import atomic_recovery_transition

    transition = atomic_recovery_transition(
        current_state="running_autonomous_steps",
        error_type="tool_schema_error",
        safety_violation_found=False,
        partial_outputs_available=True,
        recoverable=True,
    )

    assert transition["target_state"] == "partial_success"


def test_phase20q1_recovery_closure_hash_is_deterministic() -> None:
    from backend.services.aion_mission_mode.mission_failure_recovery import recovery_cryptographic_closure_hash

    first = recovery_cryptographic_closure_hash(
        failure_receipt_hash="sha256:receipt",
        trace_hash="sha256:trace",
        proof_hash="sha256:proof",
        partial_output_hashes=["sha256:b", "sha256:a"],
        target_state="blocked_for_safety",
    )
    second = recovery_cryptographic_closure_hash(
        failure_receipt_hash="sha256:receipt",
        trace_hash="sha256:trace",
        proof_hash="sha256:proof",
        partial_output_hashes=["sha256:a", "sha256:b"],
        target_state="blocked_for_safety",
    )

    assert first == second
    assert first.startswith("sha256:")


def test_phase20q1_recovery_closure_hash_changes_when_target_state_changes() -> None:
    from backend.services.aion_mission_mode.mission_failure_recovery import recovery_cryptographic_closure_hash

    first = recovery_cryptographic_closure_hash(
        failure_receipt_hash="sha256:receipt",
        trace_hash="sha256:trace",
        proof_hash="sha256:proof",
        partial_output_hashes=["sha256:a"],
        target_state="failed_recoverable",
    )
    second = recovery_cryptographic_closure_hash(
        failure_receipt_hash="sha256:receipt",
        trace_hash="sha256:trace",
        proof_hash="sha256:proof",
        partial_output_hashes=["sha256:a"],
        target_state="blocked_for_safety",
    )

    assert first != second


def test_phase20q1_full_atomic_recovery_contains_transition_and_closure_hash() -> None:
    from backend.services.aion_mission_mode.mission_failure_recovery import recover_failed_mission_with_atomic_transition

    result = recover_failed_mission_with_atomic_transition(
        mission_id="mission_001",
        mission_run_id="run_001",
        current_state="running_autonomous_steps",
        error_type="aggregate_forbidden_outcome",
        failure_reason="aggregate external messaging path",
        stopped_step_id="send",
        trace_hash="sha256:trace",
        proof_hash="sha256:proof",
        outputs=[
            {
                "output_id": "draft_001",
                "step_id": "draft",
                "artifact_type": "advert_draft",
                "business_container_path": "business_containers/home_fixed/campaigns/draft_001.json",
            }
        ],
        receipt_hashes=["sha256:receipt"],
        blocked_actions=["send_customer_message"],
        original_steps=[
            {"step_id": "draft", "action_type": "draft_offer", "lane": "creation"},
            {"step_id": "send", "action_type": "send_customer_message", "lane": "external_action"},
        ],
        safety_violation_found=True,
    )

    assert result["atomic_recovery_transition"]["target_state"] == "blocked_for_safety"
    assert result["recovery_closure_hash"].startswith("sha256:")
    assert result["recovery_hash"].startswith("sha256:")
