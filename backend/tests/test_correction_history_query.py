import os
import json
from pathlib import Path

def test_get_correction_history_smoke(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    (tmp_path / "telemetry").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)

    # No lex events -> fallback to turn_log (empty)
    from backend.modules.aion_cognition.correction_history import get_correction_history
    assert get_correction_history("x", limit=5) == []