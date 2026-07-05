from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text(encoding="utf-8")


def function_block(name):
    start = RENDERER.index(f"function {name}")
    next_fn = RENDERER.find("\n    function ", start + 1)
    if next_fn == -1:
        return RENDERER[start:]
    return RENDERER[start:next_fn]


def test_o4b1_holo_reference_fix_is_present():
    block = function_block("addAgentSeat")

    assert "AION O4B.1: fixed stale holo interaction reference" in block
    assert "let holo = null" in block
    assert "let seatInteractionObject = group" in block
    assert "seatInteractionObject = cleanClickTarget" in block


def test_o4b1_real_agent_interaction_uses_clean_click_target_not_holo():
    block = function_block("addAgentSeat")

    assert "cleanClickTarget" in block
    assert "registerInteractive(seatInteractionObject, {" in block
    assert "object: holo," not in block
    assert "registerInteractive(holo, {" not in block
    assert "mesh: holo," not in block
    assert "target: holo," not in block


def test_o4b1_holo_is_fallback_only_and_cannot_crash_real_agent_render():
    block = function_block("addAgentSeat")

    assert "const realAgentModelLoaded = !!assetRobot" in block
    assert "if (!realAgentModelLoaded)" in block
    assert "holo = assetPanel" in block
