from backend.services.aion_mission_mode.pilot_native_runtime import (
    ALLOWED_INTERNAL_SERVICE_ROUTES,
    PILOT_EXECUTOR_NAME,
    NATIVE_RUNTIME_OWNER,
    PilotInvocation,
    PilotNativeRuntimePolicy,
    boardroom_state_sync_hash,
    create_pilot_worker_state,
    kill_pilot_worker,
    reject_ui_automation_action,
    start_pilot_worker,
    validate_boardroom_state_sync,
    validate_internal_service_route,
    validate_invocation_surface,
    validate_pilot_native_policy,
)


def test_phase20z_policy_locks_aion_pilot_as_native_runtime() -> None:
    policy = PilotNativeRuntimePolicy()

    assert policy.executor_name == "AION Pilot"
    assert policy.native_runtime_owner == "aion_core"
    assert policy.is_native_aion_capability is True
    assert policy.separate_app is False
    assert policy.openclaw_clone is False
    assert policy.ui_automation_allowed is False
    assert validate_pilot_native_policy(policy) is True


def test_phase20z_constants_match_policy_language() -> None:
    assert PILOT_EXECUTOR_NAME == "AION Pilot"
    assert NATIVE_RUNTIME_OWNER == "aion_core"


def test_phase20z_invocation_starts_from_terminal_and_supervises_in_boardroom() -> None:
    invocation = PilotInvocation(
        mission_id="mission_001",
        mission_run_id="run_001",
        started_from_surface="aion_terminal",
        supervised_from_surface="boardroom_mission_control",
        workflow_canvas_visible=True,
    )

    assert validate_invocation_surface(invocation) is True


def test_phase20z_rejects_wrong_invocation_surface() -> None:
    invocation = PilotInvocation(
        mission_id="mission_001",
        mission_run_id="run_001",
        started_from_surface="separate_terminal",
        supervised_from_surface="hidden_daemon",
        workflow_canvas_visible=False,
    )

    assert validate_invocation_surface(invocation) is False


def test_phase20z_pilot_cannot_operate_by_ui_simulation() -> None:
    for action in [
        "click_ui",
        "type_into_ui",
        "scrape_ui",
        "navigate_ui",
        "cursor_move",
        "browser_ui_drive",
        "desktop_automation",
        "screen_scrape",
    ]:
        result = reject_ui_automation_action(action)
        assert result["allowed"] is False
        assert result["reason"] == "pilot_ui_automation_forbidden"


def test_phase20z_internal_service_routes_are_locked() -> None:
    assert "mission_contract" in ALLOWED_INTERNAL_SERVICE_ROUTES
    assert "mission_runtime" in ALLOWED_INTERNAL_SERVICE_ROUTES
    assert "business_container_artifacts" in ALLOWED_INTERNAL_SERVICE_ROUTES

    assert validate_internal_service_route("mission_runtime") is True
    assert validate_internal_service_route("external_ui_clicker") is False


def test_phase20z_worker_state_is_bounded_and_hashable() -> None:
    state = create_pilot_worker_state(
        mission_id="mission_001",
        mission_run_id="run_001",
        worker_id="worker_001",
    )

    assert state["status"] == "created"
    assert state["kill_switch_armed"] is False
    assert state["cpu_limit_label"] == "bounded"
    assert state["memory_limit_label"] == "bounded"
    assert state["io_channel"] == "mission_scoped_throttled"
    assert state["state_hash"].startswith("sha256:")


def test_phase20z_worker_runs_outside_primary_ui_thread() -> None:
    state = create_pilot_worker_state(
        mission_id="mission_002",
        mission_run_id="run_001",
        worker_id="worker_001",
    )
    running = start_pilot_worker(state)

    assert running["status"] == "running"
    assert running["trace_events"][-1]["async_outside_primary_ui_thread"] is True
    assert running["trace_events"][-1]["io_channel"] == "mission_scoped_throttled"


def test_phase20z_kill_switch_preserves_trace_receipts_and_partial_outputs() -> None:
    state = create_pilot_worker_state(
        mission_id="mission_003",
        mission_run_id="run_001",
        worker_id="worker_001",
    )
    state["partial_outputs"].append({"artifact_id": "artifact_001"})
    state["receipt_refs"].append("receipt_001")

    killed = kill_pilot_worker(state)

    assert killed["status"] == "killed"
    assert killed["partial_outputs"] == [{"artifact_id": "artifact_001"}]
    assert killed["receipt_refs"] == ["receipt_001"]
    assert killed["trace_events"][-1]["preserved_trace"] is True
    assert killed["trace_events"][-1]["preserved_receipts"] is True
    assert killed["trace_events"][-1]["preserved_partial_outputs"] is True


def test_phase20z_boardroom_state_sync_hash_validates() -> None:
    sync_hash = boardroom_state_sync_hash(
        mission_id="mission_004",
        mission_run_id="run_001",
        runtime_state_hash="sha256:runtime",
        worker_state_hash="sha256:worker",
    )

    assert sync_hash.startswith("sha256:")
    assert validate_boardroom_state_sync(
        expected_sync_hash=sync_hash,
        mission_id="mission_004",
        mission_run_id="run_001",
        runtime_state_hash="sha256:runtime",
        worker_state_hash="sha256:worker",
    ) is True

    assert validate_boardroom_state_sync(
        expected_sync_hash=sync_hash,
        mission_id="mission_004",
        mission_run_id="run_001",
        runtime_state_hash="sha256:runtime_changed",
        worker_state_hash="sha256:worker",
    ) is False


def test_phase20z1_preemption_checkpoint_passes_when_kill_switch_not_armed() -> None:
    from backend.services.aion_mission_mode.pilot_native_runtime import preemption_checkpoint

    state = create_pilot_worker_state(
        mission_id="mission_z1_001",
        mission_run_id="run_001",
        worker_id="worker_001",
    )

    checked = preemption_checkpoint(
        state,
        checkpoint_id="before_step_001",
        phase="before",
    )

    assert checked["status"] == "created"
    assert checked["kill_switch_armed"] is False
    assert checked["trace_events"][-1]["event_type"] == "pilot_worker_preemption_checkpoint_passed"


def test_phase20z1_stop_request_arms_kill_switch() -> None:
    from backend.services.aion_mission_mode.pilot_native_runtime import request_worker_stop

    state = create_pilot_worker_state(
        mission_id="mission_z1_002",
        mission_run_id="run_001",
        worker_id="worker_001",
    )

    stopped = request_worker_stop(state)

    assert stopped["kill_switch_armed"] is True
    assert stopped["trace_events"][-1]["next_preemption_checkpoint_must_halt"] is True


def test_phase20z1_preemption_blocks_zombie_worker_loop() -> None:
    import pytest
    from backend.services.aion_mission_mode.pilot_native_runtime import (
        PilotWorkerPreemptionError,
        preemption_checkpoint,
        request_worker_stop,
    )

    state = create_pilot_worker_state(
        mission_id="mission_z1_003",
        mission_run_id="run_001",
        worker_id="worker_001",
    )
    stopped = request_worker_stop(state, reason="operator_kill_switch")

    with pytest.raises(PilotWorkerPreemptionError) as exc:
        preemption_checkpoint(
            stopped,
            checkpoint_id="before_tool_call_001",
            phase="before",
        )

    assert "pilot_worker_preempted" in str(exc.value)
    assert "no_further_tool_execution" in str(exc.value)


def test_phase20z1_boardroom_divergence_freezes_controls() -> None:
    from backend.services.aion_mission_mode.pilot_native_runtime import (
        boardroom_divergence_action,
        boardroom_state_sync_hash,
    )

    expected = boardroom_state_sync_hash(
        mission_id="mission_z1_004",
        mission_run_id="run_001",
        runtime_state_hash="sha256:runtime",
        worker_state_hash="sha256:worker",
    )

    result = boardroom_divergence_action(
        expected_sync_hash=expected,
        mission_id="mission_z1_004",
        mission_run_id="run_001",
        runtime_state_hash="sha256:runtime_tampered",
        worker_state_hash="sha256:worker",
    )

    assert result["boardroom_trustworthy"] is False
    assert result["controls_frozen"] is True
    assert result["status_monitors_greyed"] is True
    assert result["critical_error"] == "boardroom_state_desynchronization"


def test_phase20z1_boardroom_sync_pass_keeps_controls_available() -> None:
    from backend.services.aion_mission_mode.pilot_native_runtime import (
        boardroom_divergence_action,
        boardroom_state_sync_hash,
    )

    expected = boardroom_state_sync_hash(
        mission_id="mission_z1_005",
        mission_run_id="run_001",
        runtime_state_hash="sha256:runtime",
        worker_state_hash="sha256:worker",
    )

    result = boardroom_divergence_action(
        expected_sync_hash=expected,
        mission_id="mission_z1_005",
        mission_run_id="run_001",
        runtime_state_hash="sha256:runtime",
        worker_state_hash="sha256:worker",
    )

    assert result["boardroom_trustworthy"] is True
    assert result["controls_frozen"] is False
    assert result["status_monitors_greyed"] is False
    assert result["critical_error"] is None
