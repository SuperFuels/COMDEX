from backend.services.aion_mission_mode.pilot_document_pdf_mission_demo import (
    DocumentPdfMissionRequest,
    PilotDocumentPdfMissionDemo,
    PilotDocumentPdfMissionError,
)


def _request():
    return DocumentPdfMissionRequest(
        business_id="home-fixed",
        mission_id="mission_doc_pdf_demo_001",
        mission_run_id="run_doc_pdf_demo_001",
        user_request="Build me a PDF document with X data",
        artifact_title="Home Fixed Pilot Test Document",
        artifact_format="pdf",
    )


def test_phase21f_creates_deterministic_plan():
    req = _request()
    a = PilotDocumentPdfMissionDemo.create_demo_plan(req)
    b = PilotDocumentPdfMissionDemo.create_demo_plan(req)

    assert a["plan_hash"] == b["plan_hash"]
    assert a["plan_state"] == "draft_plan_requires_review"
    assert a["live_side_effects_allowed"] is False


def test_phase21f_creates_draft_pdf_artifact_inside_business_container():
    req = _request()
    plan = PilotDocumentPdfMissionDemo.create_demo_plan(req)
    artifact = PilotDocumentPdfMissionDemo.build_draft_artifact(req, plan)

    assert artifact["artifact_type"] == "pdf"
    assert artifact["status"] == "draft_preview"
    assert artifact["business_container_path"].startswith(
        "business/home-fixed/missions/mission_doc_pdf_demo_001/runs/run_doc_pdf_demo_001/artifacts/"
    )
    assert artifact["artifact_hash"].startswith("sha256:")


def test_phase21f_receipt_binds_plan_artifact_and_path():
    req = _request()
    plan = PilotDocumentPdfMissionDemo.create_demo_plan(req)
    artifact = PilotDocumentPdfMissionDemo.build_draft_artifact(req, plan)
    receipt = PilotDocumentPdfMissionDemo.create_artifact_receipt(req, plan, artifact)

    assert receipt["plan_hash"] == plan["plan_hash"]
    assert receipt["artifact_hash"] == artifact["artifact_hash"]
    assert receipt["artifact_path"] == artifact["business_container_path"]
    assert receipt["receipt_hash"].startswith("sha256:")


def test_phase21f_receipt_blocks_all_live_side_effects():
    req = _request()
    plan = PilotDocumentPdfMissionDemo.create_demo_plan(req)
    artifact = PilotDocumentPdfMissionDemo.build_draft_artifact(req, plan)
    receipt = PilotDocumentPdfMissionDemo.create_artifact_receipt(req, plan, artifact)

    assert all(value is False for value in receipt["external_side_effects"].values())


def test_phase21f_replay_and_proof_are_non_executing_read_models():
    req = _request()
    result = PilotDocumentPdfMissionDemo.run_demo(req)

    assert result["replay"]["replay_state"] == "non_executing_read_model"
    assert result["replay"]["may_execute_tools"] is False
    assert result["replay"]["may_mutate_provider_state"] is False
    assert result["proof"]["draft_preview_only"] is True
    assert result["proof"]["live_side_effects_allowed"] is False


def test_phase21f_cockpit_view_answers_what_where_and_status():
    req = _request()
    result = PilotDocumentPdfMissionDemo.run_demo(req)

    assert result["status"] == "completed_draft_preview"
    assert result["artifact"]["business_container_path"]
    assert result["artifact"]["status"] == "draft_preview"
    assert result["receipt"]["receipt_state"] == "sealed_draft_artifact_receipt"
    assert result["safety_message"] == "AION stopped itself before doing anything risky."


def test_phase21f_cockpit_has_output_controls_but_no_live_buttons():
    result = PilotDocumentPdfMissionDemo.run_demo(_request())

    assert result["open_output_enabled"] is True
    assert result["download_output_enabled"] is True
    assert result["view_receipt_enabled"] is True
    assert result["live_action_buttons_visible"] is False


def test_phase21f_rejects_unsupported_artifact_format():
    req = DocumentPdfMissionRequest(
        business_id="home-fixed",
        mission_id="m",
        mission_run_id="r",
        user_request="Build me a binary",
        artifact_title="Bad",
        artifact_format="exe",
    )

    try:
        PilotDocumentPdfMissionDemo.create_demo_plan(req)
    except PilotDocumentPdfMissionError as exc:
        assert "unsupported artifact format" in str(exc)
    else:
        raise AssertionError("unsupported artifact format was not blocked")


def test_phase21f_rejects_parent_traversal_path():
    req = DocumentPdfMissionRequest(
        business_id="home-fixed",
        mission_id="m",
        mission_run_id="r",
        user_request="Build me a PDF",
        artifact_title="../escape",
        artifact_format="pdf",
    )
    plan = PilotDocumentPdfMissionDemo.create_demo_plan(req)

    try:
        PilotDocumentPdfMissionDemo.build_draft_artifact(req, plan)
    except PilotDocumentPdfMissionError as exc:
        assert "parent traversal" in str(exc)
    else:
        raise AssertionError("parent traversal path was not blocked")


def test_phase21f_run_is_deterministic():
    req = _request()
    a = PilotDocumentPdfMissionDemo.run_demo(req)
    b = PilotDocumentPdfMissionDemo.run_demo(req)

    assert a["cockpit_view_hash"] == b["cockpit_view_hash"]
    assert a["artifact"]["artifact_hash"] == b["artifact"]["artifact_hash"]
    assert a["receipt"]["receipt_hash"] == b["receipt"]["receipt_hash"]
