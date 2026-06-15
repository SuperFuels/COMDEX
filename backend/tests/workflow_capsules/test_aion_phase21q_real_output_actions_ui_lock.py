from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21q_lock_marker_exists():
    assert "PHASE 21Q LOCK: Pilot real output actions" in TEXT


def test_phase21q_output_action_helpers_exist():
    for token in [
        "function openAionPilotOutputPreview",
        "function downloadAionPilotOutputPreview",
        "function viewAionPilotReceiptPreview",
        "function renderAionPilotOutputPanel",
        "function closeAionPilotOutputPanel",
    ]:
        assert token in TEXT


def test_phase21q_click_handlers_exist():
    for token in [
        'target.closest("[data-aion-pilot-open-output]")',
        'target.closest("[data-aion-pilot-download-output]")',
        'target.closest("[data-aion-pilot-view-receipt]")',
        'target.closest("[data-aion-pilot-close-output-panel]")',
    ]:
        assert token in TEXT


def test_phase21q_receipt_has_human_readable_fields():
    for token in [
        "receipt_type",
        "task_type",
        "output_type",
        "artifact_hash",
        "receipt_hash",
        "replay_hash",
        "proof_hash",
        "blocked_actions",
        "safety_message",
    ]:
        assert token in TEXT


def test_phase21q_output_panel_renders():
    assert "data-aion-pilot-output-panel" in TEXT
    assert "renderAionPilotOutputPanel()" in TEXT
    assert 'typeof renderAionPilotOutputPanel === "function"' in TEXT


def test_phase21q_download_uses_blob_preview_only():
    assert "new Blob([payload]" in TEXT
    assert "aion-pilot-${safeTaskType}-draft-preview.txt" in TEXT
    assert "URL.createObjectURL(blob)" in TEXT


def test_phase21q_task_specific_preview_text_exists():
    for token in [
        "Growth Plan:",
        "Spreadsheet Draft:",
        "Website Preview Plan:",
        "Campaign Pack:",
        "Document Draft:",
        "Draft Output:",
    ]:
        assert token in TEXT


def test_phase21q_no_live_side_effect_handlers():
    phase_start = TEXT.index("PHASE 21Q LOCK: Pilot real output actions")
    phase_end = TEXT.index("END PHASE 21Q LOCK", phase_start)
    block = TEXT[phase_start:phase_end]

    for forbidden in [
        "fetch(",
        "apiPost(",
        "sendEmail(",
        "deploySite(",
        "createPayment(",
        "payment_intent(",
        "stripe.",
        "revolut.",
    ]:
        assert forbidden not in block


def test_phase21q_safety_message_retained():
    assert "AION stopped itself before doing anything risky." in TEXT


def test_phase21q_no_forbidden_live_buttons():
    for forbidden in [
        "data-aion-pilot-live-pay",
        "data-aion-pilot-live-deploy",
        "data-aion-pilot-live-send",
        "data-aion-pilot-live-post",
        "data-aion-pilot-live-book",
        "data-aion-pilot-live-escrow",
    ]:
        assert forbidden not in TEXT
