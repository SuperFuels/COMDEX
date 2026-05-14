# 📁 backend/tests/test_creative_fork_dna_switch.py
from backend.modules.creative.creative_core import emit_creative_fork, MAX_FORKS
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.dna_chain.dna_switch import (
    enable_self_growth,
    disable_self_growth,
    set_growth_factor,
    is_self_growth_enabled,
    get_growth_factor,
)

CONTAINER = "test_container_001"


def _make_seed_wave() -> WaveState:
    """
    Build a minimal WaveState using only supported __init__ kwargs.
    Set runtime fields (like coherence) afterward.
    """
    seed = WaveState(
        wave_id="seed_wave",
        glyph_data={"seed": True},
        glyph_id="seed",
        carrier_type="test_carrier",
        modulation_strategy="base",
        # NOTE: do not pass coherence here; WaveState ctor doesn't accept it.
    )
    # Set non-ctor fields after construction:
    seed.coherence = 0.99
    return seed


def _symbolic_tree():
    return {"label": "root", "children": [{"label": "A"}, {"label": "B"}]}


def test_creative_fork_respects_growth_factor():
    # Enable and widen search
    enable_self_growth(CONTAINER, actor="unit_test", reason="enable")
    set_growth_factor(CONTAINER, 2, actor="unit_test", reason="double forks")

    assert is_self_growth_enabled(CONTAINER) is True
    assert get_growth_factor(CONTAINER) == 2

    seed = _make_seed_wave()
    forks = emit_creative_fork(seed, _symbolic_tree(), CONTAINER, reason="unit_test")

    expected = min(12, MAX_FORKS * 2)
    print(f"Forks emitted: {len(forks)} | expected: {expected}")
    assert len(forks) == expected

    # quick sanity on structure
    for f in forks[:3]:
        assert getattr(f, "wave_id", None) is not None
        assert getattr(f, "container_id", None) == CONTAINER


def test_creative_fork_gated_off_yields_zero():
    # Turn gating OFF
    disable_self_growth(CONTAINER, actor="unit_test", reason="disable")
    assert is_self_growth_enabled(CONTAINER) is False

    seed = _make_seed_wave()
    forks = emit_creative_fork(seed, _symbolic_tree(), CONTAINER, reason="unit_test")
    print(f"Forks after disable: {len(forks)} | expected: 0")
    assert len(forks) == 0