from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_boardroom_reads_evidence_source_runtime_summary_from_live_bundle():
    text = APP.read_text()

    assert "evidence_source_runtime_summary" in text
    assert "goal_engine_evidence_source_runtime_summary" in text
    assert "machineTrace.evidence_source_runtime_summary" in text


def test_boardroom_reads_evidence_source_and_pointer_preview_rows():
    text = APP.read_text()

    assert "evidence_source_previews" in text
    assert "evidence_pointer_previews" in text
    assert "goal_engine_evidence_source_previews" in text
    assert "goal_engine_evidence_pointer_previews" in text


def test_boardroom_renders_supported_real_evidence_types():
    text = APP.read_text()

    for token in [
        "gmail_reply",
        "crm_lead",
        "utm_click",
        "booking",
        "payment",
        "file",
        "screenshot",
    ]:
        assert token in text


def test_boardroom_evidence_source_panel_is_visibility_only():
    text = APP.read_text()

    assert "would_read_external" in text
    assert "would_write_external" in text
    assert "would_grant_permission" in text
    assert "Evidence Source" in text or "Evidence Sources" in text


def test_focused_suite_includes_evidence_source_visibility_lock():
    text = SUITE.read_text()
    assert "test_goal_engine_boardroom_evidence_source_visibility.py" in text
