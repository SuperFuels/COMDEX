from backend.services.aion_mission_mode.pilot_cockpit_ui_contract import (
    build_pilot_cockpit_read_model,
    validate_pilot_cockpit_read_model,
)


def _model():
    return build_pilot_cockpit_read_model(
        mission_id="mission_home_fixed_demo",
        mission_run_id="run_001",
        business_id="home-fixed",
        current_step={
            "step_id": "step_003",
            "title": "Draft Home Fixed landing copy",
            "state": "running",
            "lane": "autonomous",
            "risk": "low",
        },
        steps=[
            {"step_id": "step_001", "title": "Create plan matrix", "state": "completed"},
            {"step_id": "step_002", "title": "Draft advert copy", "state": "completed"},
            {"step_id": "step_003", "title": "Draft landing copy", "state": "running"},
            {"step_id": "step_004", "title": "Domain purchase preview", "state": "waiting_approval"},
            {"step_id": "step_005", "title": "Facebook setup", "state": "waiting_human_task"},
            {"step_id": "step_006", "title": "Unapproved ad spend", "state": "blocked"},
            {"step_id": "step_007", "title": "Skipped publish", "state": "skipped"},
        ],
        artifacts=[
            {
                "artifact_id": "artifact_pdf_001",
                "artifact_type": "pdf_preview",
                "title": "Home Fixed Service Summary",
                "container_path": "businesses/home-fixed/missions/mission_home_fixed_demo/runs/run_001/artifacts/service-summary.pdf",
                "mission_id": "mission_home_fixed_demo",
                "mission_run_id": "run_001",
                "step_id": "step_003",
                "artifact_hash": "sha256:abc123",
                "status": "draft_preview",
            }
        ],
        approvals=[
            {
                "approval_id": "approval_domain_001",
                "provider": "domain_provider",
                "action": "buy_domain",
                "payload_hash": "sha256:domainpayload",
                "expiry_state": "active",
                "requires_human_approval": True,
            }
        ],
        blocked_actions=[
            {
                "blocked_action_id": "blocked_ad_spend_001",
                "action": "start_ad_campaign",
                "reason": "ad_spend_requires_exact_payload_approval",
                "safe_alternative": "prepare_ad_campaign_preview_only",
                "what_would_have_happened": "campaign_budget_would_have_been_submitted",
            }
        ],
    )


def test_phase21a_pilot_cockpit_read_model_exists():
    model = _model()
    assert model["schema_version"] == "aion.phase21a.pilot_cockpit_ui.v1"
    assert model["surface_type"] == "read_model_only"
    assert model["pilot_identity"]["name"] == "AION Pilot"
    assert model["pilot_identity"]["executor_type"] == "native_aion_runtime"


def test_phase21a_mission_stream_renders_core_states():
    stream = _model()["mission_stream"]
    assert stream["current_step"]["step_id"] == "step_003"
    assert len(stream["completed_steps"]) == 2
    assert len(stream["waiting_approval_steps"]) == 1
    assert len(stream["waiting_human_task_steps"]) == 1
    assert len(stream["blocked_steps"]) == 1
    assert len(stream["skipped_steps"]) == 1


def test_phase21a_artifact_panel_shows_container_and_provenance():
    artifact = _model()["artifacts"][0]
    assert artifact["container_visible"] is True
    assert artifact["provenance_visible"] is True
    assert artifact["container_path"].startswith("businesses/home-fixed/")
    assert artifact["artifact_hash"].startswith("sha256:")


def test_phase21a_approval_and_blocked_action_panel_visible():
    approval_surface = _model()["approval_surface"]
    assert "No money, post, deploy" in approval_surface["safety_message"]
    assert approval_surface["exact_payload_cards"][0]["requires_human_approval"] is True
    assert approval_surface["blocked_actions"][0]["safe_alternative"] == "prepare_ad_campaign_preview_only"


def test_phase21a_feedback_surface_is_governed_not_memory_mutation():
    feedback = _model()["feedback_surface"]
    assert feedback["enabled"] is True
    assert feedback["feedback_mutates_live_memory"] is False
    assert "request_revision" in feedback["allowed_feedback_actions"]
    assert "ask_where_file_was_saved" in feedback["allowed_feedback_actions"]


def test_phase21a_proof_replay_and_ets_are_non_executing():
    proof = _model()["proof_surface"]
    assert proof["proof_visible"] is True
    assert proof["replay_visible"] is True
    assert proof["receipts_visible"] is True
    assert proof["ets_preview_visible"] is True
    assert proof["replay_executes_tools"] is False
    assert proof["ets_mutates_reputation"] is False


def test_phase21a_no_raw_live_action_buttons():
    model = _model()
    assert model["raw_live_action_buttons_present"] is False
    forbidden = set(model["forbidden_live_action_labels"])
    assert "send email now" in forbidden
    assert "buy domain now" in forbidden
    assert "deploy production now" in forbidden
    assert "mutate live reputation now" in forbidden


def test_phase21a_validation_passes_for_safe_model():
    result = validate_pilot_cockpit_read_model(_model())
    assert result["allowed"] is True
    assert result["validation_state"] == "pilot_cockpit_contract_valid"
    assert result["validation_hash"].startswith("sha256:")


def test_phase21a_validation_blocks_live_action_buttons():
    model = _model()
    model["raw_live_action_buttons_present"] = True
    result = validate_pilot_cockpit_read_model(model)
    assert result["allowed"] is False
    assert "raw_live_action_buttons_present" in result["reasons"]


def test_phase21a_validation_blocks_canvas_execution_surface():
    model = _model()
    model["plan_canvas"]["canvas_is_execution_surface"] = True
    result = validate_pilot_cockpit_read_model(model)
    assert result["allowed"] is False
    assert "canvas_must_not_be_execution_surface" in result["reasons"]
