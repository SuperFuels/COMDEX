from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text(encoding="utf-8")


def forced_seats_block():
    start = RENDERER.index("function addForcedVisibleExecutiveSeats")
    end = RENDERER.index("function seatArc", start)
    return RENDERER[start:end]


def test_o4f_forced_visible_seats_prefer_real_robot_agent_glb():
    block = forced_seats_block()

    assert "AION O4F: forced visible seats use real robot_agent GLB" in block
    assert 'cloneAionBoardroomAsset("robot_agent")' in block
    assert "const realSeatRobot" in block
    assert "normalizeAionBoardroomAgentModel(realSeatRobot" in block
    assert "group.add(realSeatRobot)" in block


def test_o4f_base_glb_is_named_and_positioned_in_visible_seat_layer():
    block = forced_seats_block()

    assert "aion_o4f_real_robot_agent_${key}" in block
    assert 'targetHeight: key === "operations" ? 1.62 : 1.48' in block
    assert "realSeatRobot.position.y += 0.20" in block
    assert "realSeatRobot.position.z += 0.22" in block
    assert "realSeatRobot.visible = true" in block


def test_o4f_procedural_agent_is_fallback_only():
    block = forced_seats_block()

    assert "if (realSeatRobot)" in block
    assert "} else {" in block
    assert "aion_o4f_fallback_visible_agent_${key}" in block
    assert "group.userData.realRobotAgentLoaded = true" in block
    assert "group.userData.realRobotAgentLoaded = false" in block


def test_o4f_debug_marker_is_present():
    block = forced_seats_block()

    assert "O4F real robot_agent.glb seat renderer active" in block
