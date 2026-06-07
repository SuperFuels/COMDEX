from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
LOCK_DOC = Path("docs/rfc/aion_phase21_final_pilot_ui_validation_lock.tex").read_text(encoding="utf-8")


def test_phase21k_final_lock_doc_exists():
    assert "Phase 21K --- Final Pilot UI Validation" in LOCK_DOC
    assert "AION-PHASE21K-FINAL-PILOT-UI-VALIDATION" in LOCK_DOC


def test_phase21k_real_frontend_pilot_mount_is_visible():
    assert "data-aion-phase21x-real-frontend-pilot-mount" in APP_JS
    assert "Pilot Cockpit" in APP_JS
    assert "Mission composer" in APP_JS
    assert "Pilot stream" in APP_JS
    assert "Business container files" in APP_JS
    assert "Blocked actions" in APP_JS


def test_phase21k_pdf_demo_request_visible():
    assert "Build me a PDF document with X data" in APP_JS


def test_phase21k_business_container_path_visible():
    assert "business/home-fixed/missions/pilot_demo_pdf_mission/runs/pilot_demo_run_preview/artifacts/draft-document.pdf" in APP_JS


def test_phase21k_required_safety_message_visible():
    assert "AION stopped itself before doing anything risky." in APP_JS
    assert "No money, post, deploy, external send, booking, escrow or reputation mutation without exact approval." in APP_JS


def test_phase21k_no_forbidden_live_buttons_visible():
    forbidden = [
        "data-aion-pilot-live-pay",
        "data-aion-pilot-live-deploy",
        "data-aion-pilot-live-send",
        "data-aion-pilot-live-post",
        "data-aion-pilot-live-book",
        "data-aion-pilot-live-escrow",
    ]
    for token in forbidden:
        assert token not in APP_JS


def test_phase21k_private_reasoning_is_hidden():
    assert "Private reasoning hidden." in APP_JS


def test_phase21k_live_agents_points_to_aion_tab():
    assert "data-aion-pilot-live-agents-entry" in APP_JS
    assert "AION Pilot available from the AION tab." in APP_JS


def test_phase21k_lock_doc_records_safety_boundary():
    assert "raw credentials" in LOCK_DOC
    assert "private reasoning" in LOCK_DOC
    assert "raw tool execution" in LOCK_DOC
    assert "live payment buttons" in LOCK_DOC


def test_phase21k_lock_doc_records_final_completed_surfaces():
    for token in [
        "mission composer",
        "Pilot status",
        "Pilot stream",
        "business container save path",
        "artifact hashes",
        "receipt hashes",
        "blocked actions",
        "feedback controls",
        "mission map",
        "proof and replay links",
    ]:
        assert token in LOCK_DOC
