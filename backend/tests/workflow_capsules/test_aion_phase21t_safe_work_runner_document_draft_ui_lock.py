from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21t_lock_marker_exists():
    assert "PHASE 21T LOCK: Safe work runner and document draft generator" in TEXT


def test_phase21t_runner_functions_exist():
    for token in [
        "function runAionPilotSafeWorkPreview",
        "function buildAionPilotDocumentDraft",
        "function buildAionPilotGeneratedOutput",
        "function getAionPilotTaskSubject",
    ]:
        assert token in TEXT


def test_phase21t_approve_triggers_safe_work_runner():
    start = TEXT.index("function approveAionPilotMissionContract")
    end = TEXT.index("function reviseAionPilotMissionContract", start)
    block = TEXT[start:end]

    assert "runAionPilotSafeWorkPreview();" in block


def test_phase21t_stream_steps_exist():
    for token in [
        "Safe work started",
        "Drafting output",
        "Saving draft artifact",
        "Receipt created",
        "Safe work completed",
    ]:
        assert token in TEXT


def test_phase21t_document_draft_has_real_sections():
    for token in [
        "Executive Summary",
        "Mission",
        "Service Focus",
        "Target Customers",
        "Offer Strategy",
        "Marketing Plan",
        "Operations Plan",
        "Risks and Controls",
        "Next Steps",
        "Approval Boundary",
    ]:
        assert token in TEXT


def test_phase21t_completed_preview_hashes_exist():
    for token in [
        "sha256:frontend_completed_preview_artifact",
        "sha256:frontend_completed_preview_receipt",
        "sha256:frontend_completed_preview_replay",
        "sha256:frontend_completed_preview_proof",
    ]:
        assert token in TEXT


def test_phase21t_output_preview_uses_generated_output_text():
    assert "state.generated_output_text" in TEXT
    assert "return String(state.generated_output_text);" in TEXT


def test_phase21t_no_live_side_effects_added():
    phase_start = TEXT.index("PHASE 21T LOCK: Safe work runner and document draft generator")
    phase_end = TEXT.index("END PHASE 21T LOCK", phase_start)
    block = TEXT[phase_start:phase_end]

    for forbidden in [
        "fetch(",
        "apiPost(",
        "sendEmail(",
        "deploySite(",
        "createPayment(",
        "stripe.",
        "revolut.",
        "window.open(",
    ]:
        assert forbidden not in block


def test_phase21t_risky_actions_still_blocked():
    assert "Risky actions remain blocked until exact approval." in TEXT
    assert "It has not posted publicly, sent messages, booked work, deployed a website, spent money" in TEXT
