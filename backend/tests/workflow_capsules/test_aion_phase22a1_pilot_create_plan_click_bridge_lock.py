from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22a1_click_bridge_lock_exists():
    assert "PHASE 22A.1 LOCK: Pilot create-plan dedicated click bridge" in TEXT
    assert "installAionPilotCreatePlanClickBridge" in TEXT
    assert "__aionPilotCreatePlanClickBridgeInstalled" in TEXT


def test_phase22a1_click_bridge_targets_create_plan_button():
    assert 'target.closest("[data-aion-pilot-create-draft-mission]")' in TEXT
    assert "createAionPilotFrontendDraftMission();" in TEXT


def test_phase22a1_click_bridge_uses_capture_phase():
    assert "event.preventDefault();" in TEXT
    assert "event.stopPropagation();" in TEXT
    assert "true,\n  );" in TEXT
