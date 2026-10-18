from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text(encoding="utf-8")


def test_o4e_forced_visible_seat_helper_exists():
    assert "function addForcedVisibleExecutiveSeats" in RENDERER
    assert "AION O4E: forced visible executive seat safety layer" in RENDERER
    assert "aion_o4e_forced_visible_seat_" in RENDERER
    assert "aion_o4f_fallback_visible_agent_" in RENDERER
    assert "AION O4F: forced visible seats use real robot_agent GLB" in RENDERER


def test_o4e_forces_core_executive_departments_visible():
    for label in ["Marketing", "Sales", "Finance", "Operations", "Support", "HR"]:
        assert label in RENDERER

    assert "Brand & Growth" in RENDERER
    assert "Revenue & Pipeline" in RENDERER
    assert "Financial Stewardship" in RENDERER
    assert "Process & Efficiency" in RENDERER
    assert "Customer Success" in RENDERER
    assert "People & Culture" in RENDERER


def test_o4e_forced_visible_layer_is_added_in_executive_mode():
    assert 'if (teamMode !== "board")' in RENDERER
    assert "addForcedVisibleExecutiveSeats(root, options || {})" in RENDERER
    assert "parent.userData.aionO4EForcedVisibleSeats = true" in RENDERER
