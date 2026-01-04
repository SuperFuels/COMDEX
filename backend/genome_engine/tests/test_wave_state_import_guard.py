from __future__ import annotations

import importlib
import os
import sys


def test_wave_state_import_no_circular_warning(capsys, monkeypatch):
    # Keep it deterministic + avoid side effects
    monkeypatch.setenv("TESSARIS_DETERMINISTIC_TIME", "1")

    # Ensure a clean import
    modname = "backend.modules.glyphwave.core.wave_state"
    if modname in sys.modules:
        del sys.modules[modname]

    # Import should not explode or emit the known circular warning text
    importlib.import_module(modname)

    out = capsys.readouterr().out + capsys.readouterr().err
    assert "partially initialized module" not in out
    assert "WaveScope" not in out  # this is the noisy lazy-init warning you saw