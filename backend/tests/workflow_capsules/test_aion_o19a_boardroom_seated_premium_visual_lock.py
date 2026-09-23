from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"


def renderer_text() -> str:
    return RENDERER.read_text(encoding="utf-8")


def test_boardroom_opens_from_a_seated_table_side_camera():
    text = renderer_text()
    assert "opening frame reads as a seat at the table" in text
    assert "theta: 0" in text
    assert "radius: 4.6" in text
    assert "y: 2.5" in text
    assert "targetY: 1.45" in text
    assert "targetZ: -6.4" in text
    assert "clamp(state.radius + event.deltaY * 0.012, 3.8, 28)" in text


def test_table_has_futuristic_dimensional_material_layers_without_central_letter():
    text = renderer_text()
    assert "Futuristic executive table" in text
    assert "const pearlDeck" in text
    assert "const smartGlass" in text
    assert "const collaborationField" in text
    assert "const pedestalFoot" in text
    assert 'const coreLabel = makeTextSprite("A"' not in text


def test_agent_nameplates_draw_high_contrast_borders():
    text = renderer_text()
    assert 'const border = opts.border || "rgba(255,255,255,0)"' in text
    assert "ctx.strokeRect" in text
    assert "fontWeight: 950" in text
    assert 'background: "rgba(7, 17, 31, 0.97)"' in text


def test_board_members_have_one_compact_name_sign_without_stacked_role_or_status_plates():
    text = renderer_text()
    assert "CLEAN BOARD MEMBER NAME SIGN" in text
    assert "labelPlate.position.set(0, 2.1, 0.36)" in text
    assert "group.userData.seatRole = role" in text
    assert "liveStatusPlate" not in text


def test_executive_department_names_are_clean_single_line_overhead_signs():
    text = renderer_text()
    assert "CLEAN OVERHEAD DEPARTMENT SIGN" in text
    assert "labelPlate.position.set(0, 2.06, 0.34)" in text
    assert "restoring the former secondary role strip" in text


def test_team_switch_is_a_small_bottom_centre_interface_control_not_table_geometry():
    text = renderer_text()
    assert 'teamModeButton.dataset.aionBoardroomTeamSwitch = "true"' in text
    assert 'teamModeButton.style.left = "50%"' in text
    assert 'teamModeButton.style.bottom = "16px"' in text
    assert 'teamModeButton.style.transform = "translateX(-50%)"' in text
    assert '"Show Executive Team"' in text
    assert '"Show Board Team"' in text
    assert "new THREE.BoxGeometry(4.8, 0.12, 0.92)" not in text


def test_room_uses_one_central_display_and_a_dimensional_futuristic_feature_wall():
    text = renderer_text()
    assert "SINGLE CENTRAL BOARDROOM DISPLAY" in text
    assert "FUTURISTIC ARCHITECTURAL BACKDROP" in text
    assert "const featureWall" in text
    assert "const architecturalPanel" in text
    assert "const lightFin" in text
    assert "const horizonLight" in text
    assert "addSoftPanel(\n      root," not in text
