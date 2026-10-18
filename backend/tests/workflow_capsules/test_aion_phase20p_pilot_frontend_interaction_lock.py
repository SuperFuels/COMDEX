from backend.services.aion_mission_mode.pilot_frontend_interaction import (
    PilotFrontendContractError,
    apply_pilot_feedback,
    assert_no_live_action_buttons,
    assert_no_raw_credentials_visible,
    build_pilot_frontend_state,
    create_pdf_document_mission_preview,
)


def test_phase20p_renders_pilot_entry_and_core_panels():
    state = build_pilot_frontend_state(
        business_id="home-fixed",
        mission_id="mission_001",
        mission_run_id="run_001",
        user_request="Build me a PDF document with quote data",
        pilot_state="planning",
        plan_steps=[
            {
                "step_id": "s1",
                "title": "Draft PDF",
                "action_type": "create_pdf_preview",
                "lane": "autonomous",
            }
        ],
    )

    assert state["pilot_entry_visible"] is True
    assert state["mission_composer_visible"] is True
    assert state["plan_review_visible"] is True
    assert state["pilot_stream_visible"] is True
    assert state["artifact_panel_visible"] is True
    assert state["business_container_file_view_visible"] is True
    assert state["feedback_controls_visible"] is True
    assert state["mission_canvas_visible"] is True


def test_phase20p_pdf_document_preview_has_container_path_artifact_and_receipt():
    state = create_pdf_document_mission_preview(
        business_id="home-fixed",
        mission_id="mission_pdf",
        mission_run_id="run_pdf",
        title="Home Fixed Quote Pack",
        requested_data_label="customer quote data",
    )

    artifact = state["artifacts"][0]
    assert artifact["artifact_type"] == "pdf"
    assert artifact["path"].startswith("businesses/home-fixed/")
    assert artifact["openable"] is True
    assert artifact["downloadable"] is True
    assert state["receipts"][0]["receipt_type"] == "artifact_preview_receipt"


def test_phase20p_blocks_artifacts_outside_business_container():
    try:
        build_pilot_frontend_state(
            business_id="home-fixed",
            mission_id="m1",
            mission_run_id="r1",
            user_request="Create file",
            pilot_state="completed",
            plan_steps=[],
            artifacts=[
                {
                    "artifact_id": "bad",
                    "artifact_type": "pdf",
                    "title": "Bad path",
                    "path": "/tmp/outside.pdf",
                }
            ],
        )
    except PilotFrontendContractError as exc:
        assert "business container" in str(exc)
    else:
        raise AssertionError("Expected business container path rejection")


def test_phase20p_live_actions_do_not_expose_execute_buttons():
    state = build_pilot_frontend_state(
        business_id="home-fixed",
        mission_id="m2",
        mission_run_id="r2",
        user_request="Deploy the website",
        pilot_state="waiting_approval",
        plan_steps=[
            {
                "step_id": "deploy",
                "title": "Deploy production website",
                "action_type": "production_deploy",
                "lane": "human_approval_required",
                "can_execute_from_ui": True,
            }
        ],
    )

    step = state["plan_steps"][0]
    assert step["live_action"] is True
    assert step["requires_exact_approval"] is True
    assert step["can_execute_from_ui"] is False
    assert_no_live_action_buttons(state)


def test_phase20p_safety_messages_are_visible():
    state = create_pdf_document_mission_preview(
        business_id="home-fixed",
        mission_id="m3",
        mission_run_id="r3",
        title="Safe PDF",
        requested_data_label="X data",
    )

    assert state["safety_message"] == "AION stopped itself before doing anything risky."
    assert "completed safe work autonomously" in state["product_message"]


def test_phase20p_feedback_changes_state_without_external_mutation():
    state = create_pdf_document_mission_preview(
        business_id="home-fixed",
        mission_id="m4",
        mission_run_id="r4",
        title="Feedback PDF",
        requested_data_label="X data",
    )

    revised = apply_pilot_feedback(state, feedback_action="revise_plan", note="Make it shorter")
    assert revised["pilot_state"] == "planning"
    assert revised["last_feedback"]["mutates_external_provider"] is False
    assert revised["last_feedback"]["requires_runtime_revalidation"] is True


def test_phase20p_reject_or_stop_moves_to_blocked_for_safety():
    state = create_pdf_document_mission_preview(
        business_id="home-fixed",
        mission_id="m5",
        mission_run_id="r5",
        title="Stop PDF",
        requested_data_label="X data",
    )

    stopped = apply_pilot_feedback(state, feedback_action="stop")
    assert stopped["pilot_state"] == "blocked_for_safety"


def test_phase20p_no_raw_credentials_visible():
    state = create_pdf_document_mission_preview(
        business_id="home-fixed",
        mission_id="m6",
        mission_run_id="r6",
        title="Credential Safe PDF",
        requested_data_label="safe public data",
    )

    assert_no_raw_credentials_visible(state)


def test_phase20p_hash_is_deterministic_for_same_state():
    a = create_pdf_document_mission_preview(
        business_id="home-fixed",
        mission_id="m7",
        mission_run_id="r7",
        title="Hash PDF",
        requested_data_label="X data",
    )
    b = create_pdf_document_mission_preview(
        business_id="home-fixed",
        mission_id="m7",
        mission_run_id="r7",
        title="Hash PDF",
        requested_data_label="X data",
    )

    assert a["pilot_frontend_state_hash"] == b["pilot_frontend_state_hash"]


def test_phase20p_plan_steps_show_lanes_and_status():
    state = create_pdf_document_mission_preview(
        business_id="home-fixed",
        mission_id="m8",
        mission_run_id="r8",
        title="Lane PDF",
        requested_data_label="X data",
    )

    lanes = {step["lane"] for step in state["plan_steps"]}
    statuses = {step["status"] for step in state["plan_steps"]}

    assert "autonomous" in lanes
    assert "human_task_required" in lanes
    assert "completed" in statuses
    assert "waiting_review" in statuses
