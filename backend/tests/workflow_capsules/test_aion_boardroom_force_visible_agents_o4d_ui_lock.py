from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text(encoding="utf-8")


def add_agent_block():
    start = RENDERER.index("function addAgentSeat")
    end = RENDERER.index("function seatArc", start)
    return RENDERER[start:end]


def test_o4d_hard_visible_agent_anchor_exists():
    block = add_agent_block()

    assert "AION O4D: hard visible agent anchor" in block
    assert "agentVisibilityAnchor" in block
    assert "anchorBody" in block
    assert "anchorHead" in block
    assert "anchorFace" in block
    assert "group.add(agentVisibilityAnchor)" in block


def test_o4d_real_glb_agent_is_safely_positioned_in_front_of_chair():
    block = add_agent_block()

    assert "normalizeAionBoardroomAgentModel(assetRobot" in block
    assert "targetHeight: active ? 1.55 : 1.42" in block
    assert "assetRobot.position.set(0, 0.22, 0.34)" in block
    assert "assetRobot.visible = true" in block
    assert "group.add(assetRobot)" in block


def test_o4d_labels_and_click_target_remain_visible():
    block = add_agent_block()

    assert "labelPlate.position.set(0, 2.34, 0.54)" in block
    assert "rolePlate.position.set(0, 2.08, 0.54)" in block
    assert "cleanClickTarget.position.set(0, 1.15, 0.42)" in block
    assert "registerInteractive(seatInteractionObject, {" in block
