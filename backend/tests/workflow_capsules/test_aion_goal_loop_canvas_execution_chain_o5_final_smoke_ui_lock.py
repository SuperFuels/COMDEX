from pathlib import Path

APP = Path("desktop/mac/src/app.js")
RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")

APP_JS = APP.read_text(encoding="utf-8")
APP_LOWER = APP_JS.lower()
RENDERER_JS = RENDERER.read_text(encoding="utf-8")
RENDERER_LOWER = RENDERER_JS.lower()


def require_any(*needles):
    assert any(needle.lower() in APP_LOWER for needle in needles), f"Missing one of: {needles}"


def require_all(*needles):
    missing = [needle for needle in needles if needle.lower() not in APP_LOWER]
    assert not missing, f"Missing required markers: {missing}"


def test_o5a_core_phase_lock_files_exist():
    required_files = [
        "backend/tests/workflow_capsules/test_aion_goal_loop_generate_ab_test_from_evaluation_phase_f2_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_feedback_to_board_phase_g1_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_boardroom_feedback_decision_phase_g2_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_cross_function_analysis_phase_h1_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_cross_function_conflict_nodes_phase_h2_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_canvas_execution_controls_phase_i1_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_approval_gate_integration_phase_i2_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_business_container_persistence_phase_j1_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_replay_restore_phase_j2_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_evidence_proof_receipts_phase_k1_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_revision_history_phase_k2_ui_lock.py",
        "backend/tests/workflow_capsules/test_aion_goal_loop_founder_demo_trace_phase_n3_ui_lock.py",
    ]

    missing = [path for path in required_files if not Path(path).exists()]
    assert not missing, f"Missing phase lock files: {missing}"


def test_o5a_ab_test_from_evaluation_markers_exist_and_are_preview_safe():
    require_all(
        "source_evaluation_id",
        "variant_a",
        "variant_b",
        "approval_required",
        "boardroom_review",
        "graph_patch_preview",
    )

    require_all(
        "preview_only: true",
        "connector_call_required: false",
        "external_side_effects: false",
        "booking_created: false",
        "payment_created: false",
    )

    assert "campaign_launched: true" not in APP_LOWER
    assert "actual_execution_performed: true" not in APP_LOWER


def test_o5a_feedback_and_boardroom_decision_markers_exist():
    require_all(
        "feedback_id",
        "required_board_decision",
        "recommendation",
        "boardroom",
        "accept",
        "reject",
        "adjust",
        "request_more_data",
        "provenance",
    )

    require_all(
        "booking_created: false",
        "payment_created: false",
    )

    assert (
        "customer_message_sent: false" in APP_LOWER
        or "message_sent: false" in APP_LOWER
        or "no customer messages" in APP_LOWER
        or "customer message" in APP_LOWER
    )


def test_o5a_cross_function_analysis_and_conflict_markers_exist():
    require_all(
        "cross",
        "marketing",
        "sales",
        "operations",
        "finance",
        "support",
        "severity",
        "required_action",
        "conflict",
        "graph_patch_preview",
    )

    require_all(
        "open",
        "accepted",
        "rejected",
        "resolved",
        "graph_mutation_required: false",
    )


def test_o5a_canvas_execution_controls_are_present_and_do_not_create_second_canvas_or_pilot():
    for action in [
        "generate_department_canvases",
        "stage_agent_tasks",
        "request_approval",
        "start_safe_execution",
        "record_result",
        "evaluate_result",
        "generate_ab_test",
        "send_feedback_to_boardroom",
        "mark_goal_complete",
        "pause_loop",
        "archive_loop",
    ]:
        assert action in APP_LOWER

    require_all(
        "creates_second_canvas: false",
        "creates_second_pilot: false",
        "existing workflow canvas",
    )


def test_o5a_approval_gate_blocks_live_execution_without_exact_approval():
    require_all(
        "approval_required",
        "approval_state",
        "task_queue",
        "blocked",
        "external",
        "payment",
        "booking",
        "customer_message",
        "provenance",
    )

    require_all(
        "execution_allowed_now: false",
        "actual_execution_performed: false",
    )


def test_o5a_business_container_persistence_and_replay_are_registered_business_scoped():
    require_all(
        "registered_business",
        "business_container",
        "aion.goalloops.v1",
        "aion.goalloopcanvas.v1",
        "aion.departmentgoalloops.v1",
        "aion.boardroomgoalreview.v1",
        "aion.goalloopevidence.v1",
        "aion.goalloopreceipts.v1",
    )

    require_all(
        "replay",
        "restore",
        "business_container_id",
        "stale",
        "preview_only: true",
        "actual_container_write_performed: false",
    )

    risky_defaults = [
        "business_id: \"home_fixed\"",
        "business_id: 'home_fixed'",
        "business_id: \"costa-conexion\"",
        "business_id: 'costa-conexion'",
        "business_id: \"costa_conexion\"",
        "business_id: 'costa_conexion'",
    ]
    leaked = [item for item in risky_defaults if item.lower() in APP_LOWER]
    assert not leaked, f"Hard-coded runtime business default leaked: {leaked}"


def test_o5a_evidence_receipts_and_audit_trail_markers_exist():
    require_all(
        "evidence",
        "receipt_hash",
        "proof",
        "provenance",
        "revision",
        "before",
        "after",
        "timestamp",
    )

    require_any(
        "Boardroom",
        "Central Pilot",
        "Department Pilot",
        "Evaluation engine",
        "A/B test generator",
    )


def test_o5a_final_preview_chain_mounts_with_existing_central_pilot():
    # The final preview chain must coexist with the existing central Pilot.
    # Do not over-lock exact order because earlier phase panels may be mounted
    # in the broader Pilot cockpit area while still preserving the one-Pilot rule.
    required = [
        "renderAionGoalLoopExecutiveDecisionPackagePanel",
        "renderAionGoalLoopBoardroomDecisionCapturePanel",
        "renderAionGoalLoopApprovedActionStagingPanel",
        "renderAionGoalLoopGuardedExecutionHandoffPanel",
        "renderAionGoalLoopFounderDemoTracePanel",
        "renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())",
    ]

    for marker in required:
        assert marker in APP_JS

    assert "creates_second_canvas: false" in APP_JS
    assert "creates_second_pilot: false" in APP_JS
    assert APP_JS.count("renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())") >= 1


def test_o5a_boardroom_visual_modes_have_real_agent_safety_layers():
    assert "O4F real robot_agent.glb seat renderer active" in RENDERER_JS
    assert "O4G board team robot_agent.glb seat renderer active" in RENDERER_JS
    assert "addForcedVisibleExecutiveSeats(root, options || {})" in RENDERER_JS
    assert "addForcedVisibleBoardTeamSeats(root, options || {})" in RENDERER_JS
    assert 'cloneAionBoardroomAsset("robot_agent")' in RENDERER_JS
