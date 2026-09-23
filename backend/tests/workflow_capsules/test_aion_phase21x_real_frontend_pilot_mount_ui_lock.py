from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21x_lock_marker_exists():
    assert "PHASE 21X LOCK: Real frontend Pilot cockpit mount" in TEXT
    assert "data-aion-phase21x-real-frontend-pilot-mount" in TEXT


def test_phase21x_renderer_and_snapshot_exist():
    assert "function renderAionPilotCockpitPanel" in TEXT
    assert "function getAionPilotCockpitSnapshot" in TEXT



def test_phase21x_aion_chat_surface_points_to_pilot_cockpit_location():
    start = TEXT.index("function renderAionChatSurface()")
    end = TEXT.index("function renderAionToolMiniCard", start)
    block = TEXT[start:end]
    assert "installAionPilotCockpitStyles();" in block
    assert "data-aion-pilot-chat-pointer" in block
    assert "Live Agents → Aion" in block


def test_phase21x_full_cockpit_not_mounted_inside_aion_chat_surface():
    start = TEXT.index("function renderAionChatSurface()")
    end = TEXT.index("function renderAionToolMiniCard", start)
    block = TEXT[start:end]
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" not in block

def test_phase21x_visible_sections_exist():
    for token in [
        "Pilot Cockpit",
        "Mission composer",
        "Pilot stream",
        "Plan / mission map",
        "Business container files",
        "Blocked actions",
    ]:
        assert token in TEXT


def test_phase21x_document_pdf_request_visible():
    assert "Build me a PDF document with X data" in TEXT


def test_phase21x_container_path_visible():
    assert "business/home-fixed/missions/pilot_demo_pdf_mission/runs/pilot_demo_run_preview/artifacts/draft-document.pdf" in TEXT


def test_phase21x_safety_messages_visible():
    assert "AION stopped itself before doing anything risky." in TEXT
    assert "No money, post, deploy, external send, booking, escrow or reputation mutation without exact approval." in TEXT


def test_phase21x_private_reasoning_hidden():
    assert "Private reasoning hidden." in TEXT


def test_phase21x_no_live_external_buttons_by_default():
    for forbidden in [
        "data-aion-pilot-live-pay",
        "data-aion-pilot-live-deploy",
        "data-aion-pilot-live-send",
        "data-aion-pilot-live-post",
        "data-aion-pilot-live-book",
        "data-aion-pilot-live-escrow",
    ]:
        assert forbidden not in TEXT


def test_phase21x_live_agents_points_to_aion_tab():
    assert "data-aion-pilot-live-agents-entry" in TEXT
    assert "AION Pilot available from the AION tab." in TEXT
