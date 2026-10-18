from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text(encoding="utf-8")


def function_block(name):
    start = RENDERER.index(f"function {name}")
    next_fn = RENDERER.find("\n  function ", start + 1)
    alt_next = RENDERER.find("\n    function ", start + 1)
    candidates = [i for i in [next_fn, alt_next] if i != -1]
    end = min(candidates) if candidates else len(RENDERER)
    return RENDERER[start:end]


def test_o4c_mesh_validation_and_normalization_helpers_exist():
    assert "function aionBoardroomObjectHasVisibleMesh" in RENDERER
    assert "function normalizeAionBoardroomAgentModel" in RENDERER
    assert "AION O4C: normalize real GLB boardroom agent" in RENDERER


def test_o4c_empty_glbs_do_not_suppress_primitive_fallbacks():
    block = function_block("cloneAionBoardroomAsset")

    assert "aionBoardroomObjectHasVisibleMesh(clone)" in block
    assert "return null" in block


def test_o4c_real_robot_is_normalized_and_given_visible_presence_marker():
    block = RENDERER[RENDERER.index("function addAgentSeat"):RENDERER.index("function seatArc")]

    assert "normalizeAionBoardroomAgentModel(assetRobot" in block
    assert "targetHeight: active ? 1.55 : 1.42" in block
    assert "aion_real_agent_model_${key}" in block
    assert "agentVisibilityAnchor" in block
    assert "group.add(assetRobot)" in block


def test_o4c_labels_are_moved_above_visible_real_agent():
    block = RENDERER[RENDERER.index("function addAgentSeat"):RENDERER.index("function seatArc")]

    assert "labelPlate.position.set(0, 2.34, 0.54)" in block
    assert "rolePlate.position.set(0, 2.08, 0.54)" in block
