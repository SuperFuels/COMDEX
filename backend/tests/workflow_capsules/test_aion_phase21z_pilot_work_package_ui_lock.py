from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21z_work_package_helpers_exist():
    assert "function buildAionPilotWorkPackage" in TEXT
    assert "function renderAionPilotWorkPackageCard" in TEXT
    assert "function normaliseAionPilotPreviewText" in TEXT


def test_phase21z_main_plan_card_is_work_package_not_safety_wall():
    assert 'data-aion-phase21z-work-package-card' in TEXT
    assert '<div class="aion-pilot-card-kicker">Work package</div>' in TEXT
    assert "Deliverables" in TEXT
    assert "Draft steps" in TEXT
    assert "data-aion-phase21z-safety-helper" in TEXT


def test_phase21z_supports_website_work_package():
    for token in [
        "Website build package",
        "Homepage structure",
        "Hero message",
        "Services section",
        "SEO/local keywords",
        "Launch checklist",
    ]:
        assert token in TEXT


def test_phase21z_approve_button_is_safe_draft_work():
    assert "Approve safe draft work" in TEXT


def test_phase21z_output_panel_normalises_literal_newlines():
    assert "normaliseAionPilotPreviewText" in TEXT
    assert "replace(/\\\\n/g" in TEXT


def test_phase21z_lrm_and_process_logs_remain_hidden_or_secondary():
    assert "data-aion-phase21y-process-log-drawer" in TEXT
    assert "data-aion-lrm-technical-details" in TEXT
