from backend.services.aion_mission_mode.mission_contract_integrity import (
    create_mission_threat_model_entry,
    detect_disguised_action,
    evaluate_mission_contract_integrity,
)


def test_phase20p_safe_steps_pass_integrity() -> None:
    result = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=[
            {"step_id": "research", "action_type": "research_service_angle", "lane": "research"},
            {"step_id": "draft", "action_type": "draft_offer", "lane": "creation"},
        ],
    )

    assert result["integrity_passed"] is True
    assert result["runtime_mount_allowed"] is True
    assert result["mission_runtime_state"] == "integrity_passed"
    assert result["integrity_hash"].startswith("sha256:")


def test_phase20p_detects_disguised_external_message() -> None:
    finding = detect_disguised_action(
        {
            "step_id": "safe_draft",
            "action_type": "draft_customer_message",
            "payload": {"later": "send WhatsApp to customer"},
        }
    )

    assert finding is not None
    assert finding.outcome == "external_message_send"


def test_phase20p_detects_disguised_payment_capture() -> None:
    result = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=[
            {
                "step_id": "payment_preview",
                "action_type": "draft_payment_note",
                "payload": {"instruction": "charge card after approval"},
            }
        ],
    )

    assert result["integrity_passed"] is False
    assert result["mission_runtime_state"] == "waiting_human_review"


def test_phase20p_detects_aggregate_external_message_sequence() -> None:
    result = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=[
            {"step_id": "a", "action_type": "draft_customer_message"},
            {"step_id": "b", "action_type": "resolve_customer_contact"},
            {"step_id": "c", "action_type": "send_customer_message"},
        ],
    )

    assert result["integrity_passed"] is False
    assert result["mission_runtime_state"] == "blocked_for_safety"
    assert result["findings"][0]["outcome"] == "external_message_send"


def test_phase20p_detects_aggregate_payment_sequence() -> None:
    result = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=[
            {"step_id": "a", "action_type": "quote_preview"},
            {"step_id": "b", "action_type": "collect_payment_details"},
            {"step_id": "c", "action_type": "capture_payment"},
        ],
    )

    assert result["findings"][0]["outcome"] == "payment_capture"


def test_phase20p_detects_aggregate_booking_sequence() -> None:
    result = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=[
            {"step_id": "a", "action_type": "availability_preview"},
            {"step_id": "b", "action_type": "select_time_slot"},
            {"step_id": "c", "action_type": "create_booking"},
        ],
    )

    assert result["findings"][0]["outcome"] == "booking_creation"


def test_phase20p_detects_aggregate_deployment_sequence() -> None:
    result = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=[
            {"step_id": "a", "action_type": "draft_page"},
            {"step_id": "b", "action_type": "build_live_bundle"},
            {"step_id": "c", "action_type": "deploy_production"},
        ],
    )

    assert result["findings"][0]["outcome"] == "production_deployment"


def test_phase20p_detects_tool_combination_external_bypass() -> None:
    result = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=[
            {"step_id": "a", "action_type": "draft_note", "tool": "draft_tool"},
            {"step_id": "b", "action_type": "lookup_contact", "tool": "contact_lookup_tool"},
            {"step_id": "c", "action_type": "queue_send", "tool": "external_send_tool"},
        ],
    )

    assert result["findings"][0]["finding_type"] == "tool_combination_bypass"
    assert result["runtime_mount_allowed"] is False


def test_phase20p_detects_tool_combination_payment_bypass() -> None:
    result = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=[
            {"step_id": "a", "action_type": "draft_quote", "tool": "quote_tool"},
            {"step_id": "b", "action_type": "prep_payload", "tool": "payment_payload_tool"},
            {"step_id": "c", "action_type": "run_capture", "tool": "payment_capture_tool"},
        ],
    )

    assert result["findings"][0]["outcome"] == "payment_capture"


def test_phase20p_integrity_hash_is_deterministic() -> None:
    steps = [{"step_id": "draft", "action_type": "draft_offer", "lane": "creation"}]

    first = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=steps,
    )
    second = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=steps,
    )

    assert first["integrity_hash"] == second["integrity_hash"]


def test_phase20p_integrity_hash_changes_when_findings_change() -> None:
    first = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=[{"step_id": "draft", "action_type": "draft_offer"}],
    )
    second = evaluate_mission_contract_integrity(
        mission_id="mission_001",
        mission_run_id="run_001",
        steps=[{"step_id": "deploy", "action_type": "deploy_production"}],
    )

    assert first["integrity_hash"] != second["integrity_hash"]


def test_phase20p_threat_model_entry_is_deterministic() -> None:
    first = create_mission_threat_model_entry(
        mission_id="mission_home_fixed",
        observed_pattern="safe steps combined into external send",
        mitigation="aggregate sequence blocked",
    )
    second = create_mission_threat_model_entry(
        mission_id="mission_home_fixed",
        observed_pattern="safe steps combined into external send",
        mitigation="aggregate sequence blocked",
    )

    assert first["threat_model_entry_hash"] == second["threat_model_entry_hash"]
    assert first["source"] == "home_fixed_demo_run"
