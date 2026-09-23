from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21p_lock_marker_exists():
    assert "PHASE 21P LOCK: Universal Pilot stream output labels" in TEXT


def test_phase21p_helpers_exist():
    assert "function getAionPilotOutputPreparedLabel" in TEXT
    assert "function getAionPilotOutputPreparedDetail" in TEXT


def test_phase21p_no_hardcoded_pdf_stream_label():
    assert 'label: "Draft PDF artifact prepared"' not in TEXT


def test_phase21p_stream_uses_universal_plan_label():
    assert "label: getAionPilotOutputPreparedLabel(universalPlan)" in TEXT
    assert "detail: getAionPilotOutputPreparedDetail(universalPlan)" in TEXT


def test_phase21p_growth_social_detail_exists():
    assert "Prepared growth strategy, content drafts and approval-gated social actions." in TEXT


def test_phase21p_spreadsheet_detail_exists():
    assert "Prepared spreadsheet draft and business model structure inside the business container." in TEXT


def test_phase21p_website_detail_exists():
    assert "Prepared website preview draft and stopped before production deployment." in TEXT


def test_phase21p_advertising_detail_exists():
    assert "Prepared campaign preview and ad drafts, with ad spend blocked until approval." in TEXT


def test_phase21p_document_detail_exists():
    assert "Prepared document draft inside the business container." in TEXT


def test_phase21p_safety_boundary_unchanged():
    assert "Live external actions blocked" in TEXT
    assert "No send, deploy, payment, post, booking or escrow without exact approval" in TEXT
