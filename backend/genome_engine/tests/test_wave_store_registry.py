from __future__ import annotations

from backend.modules.glyphwave.core.wave_store import (
    ENTANGLED_WAVE_STORE,
    register_entangled_wave,
    get_entangled_wave,
)


class _DummyEntangledWave:
    pass


def test_wave_store_register_and_get_is_stable():
    # isolate test from global state
    ENTANGLED_WAVE_STORE.clear()

    ew = _DummyEntangledWave()
    register_entangled_wave("c1", ew)

    assert get_entangled_wave("c1") is ew
    assert get_entangled_wave("missing") is None
