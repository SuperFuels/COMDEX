from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase17f_website_intake_installation_panel_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_phase17f_lock_markers_exist():
    text = APP.read_text()
    css = CSS.read_text()

    assert "PHASE 17F LOCK: Website intake installation panel" in text
    assert "PHASE 17F LOCK: Website intake installation panel" in css
    assert DOC.exists()


def test_phase17f_installation_panel_is_mounted():
    text = APP.read_text()

    assert "function renderAionWebsiteIntakeInstallationPanel" in text
    assert "renderAionWebsiteIntakeInstallationPanel()" in text
    assert "data-aion-phase17f-website-intake-installation" in text


def test_phase17f_has_three_business_friendly_install_modes():
    text = APP.read_text()

    for phrase in [
        "Connect Your Website Enquiries",
        "Email Forwarding Setup",
        "Existing Form Webhook",
        "AION Generated Form / Embed",
        "Best for non-technical businesses",
        "Best for a web designer or developer",
        "Best when the business needs a ready-made form",
    ]:
        assert phrase in text


def test_phase17f_email_forwarding_setup_is_visible():
    text = APP.read_text()

    for phrase in [
        "home_fixed@intake.tessaris.ai",
        "Forward contact-form emails to the intake mailbox",
        "No website code changes required",
    ]:
        assert phrase in text


def test_phase17f_webhook_setup_is_visible():
    text = APP.read_text()

    for phrase in [
        "https://api.tessaris.ai/public/intake/home_fixed",
        "Send name, phone, email, message, service, location, and urgency",
        "website_intake.trigger.created",
    ]:
        assert phrase in text


def test_phase17f_embed_setup_is_visible():
    text = APP.read_text()

    for phrase in [
        "https://cdn.tessaris.ai/intake-widget.js",
        'data-business-id="home_fixed"',
        'data-mode="form"',
        "AION renders the enquiry form or floating request button",
    ]:
        assert phrase in text


def test_phase17f_css_selectors_exist():
    css = CSS.read_text()

    for selector in [
        ".aion-website-intake-installation",
        ".aion-intake-install-grid",
        ".aion-intake-install-card",
        ".aion-intake-install-copy-box",
        ".aion-intake-install-dev-details",
    ]:
        assert selector in css


def test_phase17f_is_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_aion_phase17f_website_intake_installation_panel_lock.py" in suite

def test_phase17f_installation_panel_is_mounted_in_active_boardroom_layout():
    text = APP.read_text()
    ticket_mount = "${renderAionPhase17EBoardroomTicketCard()}"
    install_mount = "${renderAionWebsiteIntakeInstallationPanel()}"

    assert ticket_mount in text
    assert install_mount in text

    ticket_index = text.find(ticket_mount)
    install_index = text.find(install_mount)

    assert install_index > ticket_index
    assert install_index < text.find("/* PHASE 17E LOCK:")

    assert "Website Intake Installation" in text
    assert "Connect Your Website Enquiries" in text
    assert "Email Forwarding Setup" in text
    assert "Existing Form Webhook" in text
    assert "AION Generated Form / Embed" in text

