from pathlib import Path

APP = Path("desktop/mac/src/app.js")
TEXT = APP.read_text()


def test_phase17f_installation_panel_renderer_exists() -> None:
    assert "function renderAionWebsiteIntakeInstallationPanel()" in TEXT
    assert "Website Intake Installation" in TEXT
    assert "Connect Your Website Enquiries" in TEXT


def test_phase17f_panel_is_mounted_in_active_boardroom_layout() -> None:
    ticket_mount = "${renderAionPhase17EBoardroomTicketCard()}"
    install_mount = "${renderAionWebsiteIntakeInstallationPanel()}"

    assert ticket_mount in TEXT
    assert install_mount in TEXT
    assert TEXT.index(ticket_mount) < TEXT.index(install_mount)


def test_phase17f_has_three_install_paths() -> None:
    assert "Email Forwarding Setup" in TEXT
    assert "Existing Form Webhook" in TEXT
    assert "AION Generated Form / Embed" in TEXT


def test_phase17f_no_longer_uses_fake_hosted_mailbox() -> None:
    assert "home_fixed@intake.tessaris.ai" not in TEXT


def test_phase17f_shows_realistic_setup_actions() -> None:
    assert "Copy webhook endpoint" in TEXT
    assert "Gmail/Vault" in TEXT or "Gmail" in TEXT


def test_phase17f_keeps_developer_payload_example() -> None:
    assert "Developer payload example" in TEXT
    assert '"business_id": "home_fixed"' in TEXT
    assert '"source": "website_form"' in TEXT


def test_phase17f_preserves_public_intake_concepts() -> None:
    assert "website_intake.trigger.created" in TEXT
    assert "home_fixed_new_enquiry" in TEXT
    assert "guarded_preview" in TEXT


def test_phase17f_safe_mode_language_remains_visible() -> None:
    assert "No booking" in TEXT
    assert "No payment" in TEXT
    assert "No escrow" in TEXT
    assert "No external message" in TEXT
    assert "No live chain write" in TEXT
