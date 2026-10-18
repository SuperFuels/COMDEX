from backend.services.aion_mission_mode.human_task_cards import (
    complete_human_task,
    create_facebook_page_human_task,
    create_human_task_card,
    create_phone_verification_human_task,
    human_task_from_plan_step,
    submit_human_task_evidence,
    validate_human_task_evidence,
)


def test_phase20n3_creates_human_task_card() -> None:
    card = create_human_task_card(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="create_facebook",
        title="Create Facebook page",
        reason="Requires real account ownership.",
        instructions=["Create page.", "Submit URL."],
        required_evidence_type="url",
        required_evidence_fields=["page_url"],
        provider="Meta",
    )

    assert card["status"] == "waiting_human_task"
    assert card["blocking_status"] is True
    assert card["resume_condition"] == "required_evidence_validated"
    assert card["task_hash"].startswith("sha256:")


def test_phase20n3_facebook_page_task_has_url_evidence() -> None:
    card = create_facebook_page_human_task(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_name="Home Fixed",
    )

    assert card["provider"] == "Meta"
    assert card["required_evidence_type"] == "url"
    assert card["required_evidence_fields"] == ["page_url"]
    assert "Facebook" in card["title"]


def test_phase20n3_phone_verification_task_has_confirmation_code_evidence() -> None:
    card = create_phone_verification_human_task(
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="GoDaddy",
    )

    assert card["provider"] == "GoDaddy"
    assert card["required_evidence_type"] == "confirmation_code"
    assert card["required_evidence_fields"] == ["confirmation_code"]


def test_phase20n3_missing_evidence_prevents_resume() -> None:
    card = create_facebook_page_human_task(
        mission_id="mission_001",
        mission_run_id="run_001",
    )

    result = validate_human_task_evidence(
        task_card=card,
        evidence_record=None,
    )

    assert result["valid"] is False
    assert result["resume_allowed"] is False
    assert result["mission_state"] == "waiting_human_task"
    assert result["reason"] == "missing_evidence"


def test_phase20n3_missing_required_field_prevents_resume() -> None:
    card = create_facebook_page_human_task(
        mission_id="mission_001",
        mission_run_id="run_001",
    )
    evidence = submit_human_task_evidence(
        task_card=card,
        submitted_by="kevin",
        evidence={"wrong_field": "https://facebook.com/homefixed"},
    )

    result = validate_human_task_evidence(
        task_card=card,
        evidence_record=evidence,
    )

    assert result["valid"] is False
    assert result["resume_allowed"] is False
    assert result["missing_fields"] == ["page_url"]


def test_phase20n3_valid_evidence_allows_resume() -> None:
    card = create_facebook_page_human_task(
        mission_id="mission_001",
        mission_run_id="run_001",
    )
    evidence = submit_human_task_evidence(
        task_card=card,
        submitted_by="kevin",
        evidence={"page_url": "https://facebook.com/homefixed"},
    )

    result = validate_human_task_evidence(
        task_card=card,
        evidence_record=evidence,
    )

    assert result["valid"] is True
    assert result["resume_allowed"] is True
    assert result["mission_state"] == "running_autonomous_steps"
    assert result["reason"] == "evidence_validated"


def test_phase20n3_complete_human_task_with_valid_evidence() -> None:
    card = create_facebook_page_human_task(
        mission_id="mission_001",
        mission_run_id="run_001",
    )
    evidence = submit_human_task_evidence(
        task_card=card,
        submitted_by="kevin",
        evidence={"page_url": "https://facebook.com/homefixed"},
    )

    completion = complete_human_task(
        task_card=card,
        evidence_record=evidence,
        completed_by="kevin",
    )

    assert completion["completed"] is True
    assert completion["status"] == "completed"
    assert completion["resume_allowed"] is True
    assert completion["completion_hash"].startswith("sha256:")


def test_phase20n3_rejects_completion_with_invalid_evidence() -> None:
    card = create_facebook_page_human_task(
        mission_id="mission_001",
        mission_run_id="run_001",
    )
    evidence = submit_human_task_evidence(
        task_card=card,
        submitted_by="kevin",
        evidence={"page_url": ""},
    )

    completion = complete_human_task(
        task_card=card,
        evidence_record=evidence,
        completed_by="kevin",
    )

    assert completion["completed"] is False
    assert completion["status"] == "evidence_rejected"
    assert completion["resume_allowed"] is False
    assert completion["mission_state"] == "waiting_human_task"


def test_phase20n3_evidence_hash_is_deterministic() -> None:
    card = create_facebook_page_human_task(
        mission_id="mission_001",
        mission_run_id="run_001",
    )

    first = submit_human_task_evidence(
        task_card=card,
        submitted_by="kevin",
        evidence={"page_url": "https://facebook.com/homefixed"},
    )
    second = submit_human_task_evidence(
        task_card=card,
        submitted_by="kevin",
        evidence={"page_url": "https://facebook.com/homefixed"},
    )

    assert first["evidence_hash"] == second["evidence_hash"]


def test_phase20n3_validation_hash_is_deterministic() -> None:
    card = create_facebook_page_human_task(
        mission_id="mission_001",
        mission_run_id="run_001",
    )
    evidence = submit_human_task_evidence(
        task_card=card,
        submitted_by="kevin",
        evidence={"page_url": "https://facebook.com/homefixed"},
    )

    first = validate_human_task_evidence(task_card=card, evidence_record=evidence)
    second = validate_human_task_evidence(task_card=card, evidence_record=evidence)

    assert first["validation_hash"] == second["validation_hash"]


def test_phase20n3_human_task_from_facebook_plan_step() -> None:
    step = {
        "step_id": "facebook_page",
        "action_type": "create_real_facebook_account",
        "business_name": "Home Fixed",
        "provider": "Meta",
    }

    card = human_task_from_plan_step(
        mission_id="mission_001",
        mission_run_id="run_001",
        step=step,
    )

    assert card["step_id"] == "facebook_page"
    assert card["required_evidence_type"] == "url"
    assert card["required_evidence_fields"] == ["page_url"]


def test_phase20n3_human_task_from_generic_plan_step() -> None:
    step = {
        "step_id": "take_photos",
        "action_type": "take_real_job_photos",
        "title": "Take real job photos",
        "reason": "Requires physical site photos.",
        "instructions": ["Take photos.", "Upload photo evidence."],
        "required_evidence_type": "uploaded_file_hash",
        "required_evidence_fields": ["file_hash"],
    }

    card = human_task_from_plan_step(
        mission_id="mission_001",
        mission_run_id="run_001",
        step=step,
    )

    assert card["step_id"] == "take_photos"
    assert card["required_evidence_type"] == "uploaded_file_hash"
    assert card["required_evidence_fields"] == ["file_hash"]
