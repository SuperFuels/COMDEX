from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text(encoding="utf-8")


def function_block(name):
    start = RENDERER.index(f"function {name}")
    next_fn = RENDERER.find("\n    function ", start + 1)
    if next_fn == -1:
        return RENDERER[start:]
    return RENDERER[start:next_fn]


def test_real_glb_agent_is_visual_focus_and_old_overlay_is_fallback_only():
    block = function_block("addAgentSeat")

    assert "AION O4B: clean real GLB agent presentation" in block
    assert "const realAgentModelLoaded = !!assetRobot" in block
    assert "if (!realAgentModelLoaded)" in block
    assert "large hologram monitor/card across the model body" in block


def test_clean_agent_keeps_label_role_and_click_target_without_body_blocking_card():
    block = function_block("addAgentSeat")

    assert "labelPlate.position.set(0, 2.34, 0.54)" in block
    assert "rolePlate.position.set(0, 2.08, 0.54)" in block
    assert "cleanClickTarget" in block
    assert "opacity: 0.001" in block
    assert "cleanBaseRing" in block
    assert "No body-blocking monitor panel" in block


def test_old_hologram_panel_not_always_drawn_over_real_robot():
    block = function_block("addAgentSeat")

    marker = "if (!realAgentModelLoaded)"
    idx = block.index(marker)

    # assetPanel/holo is still allowed only inside the fallback branch after the guard.
    before_guard = block[:idx]
    assert "assetPanel" in block
    assert "let holo = assetPanel" not in before_guard
    assert "initial.position.set(0, 1.17, 1.02)" in block
