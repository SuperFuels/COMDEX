from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase17f_business_website_intake_installation_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_phase17f_lock_markers_exist():
    text = APP.read_text()
    css = CSS.read_text()

    assert "PHASE 17F LOCK: Business Website Intake Installation" in text
    assert "PHASE 17F LOCK: Business Website Intake Installation" in css
    assert DOC.exists()


def test_phase17f_defines_three_install_options():
    text = APP.read_text()

    for phrase in [
        "Email Forwarding Setup",
        "Existing Form Webhook",
        "AION Generated Form / Embed",
        "email_forwarding",
        "existing_form_webhook",
        "aion_generated_form",
    ]:
        assert phrase in text


def test_phase17f_email_forwarding_is_default_small_business_route():
    text = APP.read_text()

    for phrase in [
        "Non-technical business owner",
        "existing website form already sends enquiries to email",
        "homefixed@intake.aion.local",
        "AION reads the enquiry, normalises it, and creates a business ticket",
    ]:
        assert phrase in text


def test_phase17f_webhook_option_exists_for_web_designer():
    text = APP.read_text()

    for phrase in [
        "Web designer / developer",
        "POST /api/aion/public-intake/home_fixed",
        "Keep the current website form working as normal",
        "ticket preview ID",
    ]:
        assert phrase in text


def test_phase17f_embed_option_exists_for_aion_generated_form():
    text = APP.read_text()

    for phrase in [
        "AION onboarding / replacement form",
        "aion-business-intake",
        "data-business-id",
        "data-mode",
        "enquiry-form",
    ]:
        assert phrase in text


def test_phase17f_is_mounted_in_boardroom():
    text = APP.read_text()

    assert "function renderAionBusinessWebsiteIntakeInstallationPanel" in text
    assert "renderAionBusinessWebsiteIntakeInstallationPanel()" in text
    assert "data-aion-phase17f-business-installation" in text


def test_phase17f_preserves_guarded_preview_contract():
    text = APP.read_text()

    for phrase in [
        "website_intake.trigger.created",
        "guarded_preview",
        "home_fixed",
        "home_fixed_new_enquiry",
        "no booking, payment, escrow, external message, or chain write",
    ]:
        assert phrase in text


def test_phase17f_css_exists():
    css = CSS.read_text()

    for selector in [
        ".aion-phase17f-installation-panel",
        ".aion-phase17f-install-grid",
        ".aion-phase17f-install-card",
        ".aion-phase17f-code-line",
        ".aion-phase17f-example",
    ]:
        assert selector in css


def test_phase17f_is_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_aion_phase17f_business_website_intake_installation_lock.py" in suite
