from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text(encoding="utf-8")


def board_team_block():
    start = RENDERER.index("function addForcedVisibleBoardTeamSeats")
    end = RENDERER.index("function seatArc", start)
    return RENDERER[start:end]


def test_o4g_forced_visible_board_team_helper_exists():
    block = board_team_block()

    assert "AION O4G: forced visible board team seat safety layer" in block
    assert "function addForcedVisibleBoardTeamSeats" in RENDERER
    assert "aion_o4g_forced_visible_board_seat_" in block
    assert "O4G board team robot_agent.glb seat renderer active" in block


def test_o4g_board_team_seats_are_ceo_aion_openai():
    block = board_team_block()

    assert '"ceo", "CEO", "Strategic Leadership"' in block
    assert '"aion", "AION", "Core Intelligence"' in block
    assert '"openai", "OpenAI", "Model Provider"' in block


def test_o4g_board_team_prefers_real_robot_agent_glb():
    block = board_team_block()

    assert 'cloneAionBoardroomAsset("robot_agent")' in block
    assert "const realBoardRobot" in block
    assert "normalizeAionBoardroomAgentModel(realBoardRobot" in block
    assert "group.add(realBoardRobot)" in block
    assert "aion_o4g_real_board_robot_agent_${key}" in block


def test_o4g_board_team_is_used_when_team_mode_is_board():
    assert 'if (teamMode !== "board")' in RENDERER
    assert "addForcedVisibleExecutiveSeats(root, options || {})" in RENDERER
    assert "addForcedVisibleBoardTeamSeats(root, options || {})" in RENDERER
