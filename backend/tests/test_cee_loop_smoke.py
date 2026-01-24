# backend/tests/test_cee_loop_smoke.py
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _write_dummy_ral_metrics(data_root: Path) -> None:
    """
    Seed minimal RAL metrics so CAU has metrics in pytest sandbox.
    """
    p = data_root / "learning" / "ral_metrics.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "timestamp": 0,
        "mean_phi": 0.0,
        "stability": 1.0,
        "drift_entropy": 0.0,
    }
    p.write_text(json.dumps(line) + "\n", encoding="utf-8")


@pytest.mark.timeout(30)
def test_cee_loop_smoke(tmp_path, monkeypatch):
    """
    Smoke test: CEE → CAU → LexMemory → Analytics produces expected artifacts.
    """

    # IMPORTANT: make all relative "data/..." writes land in the sandbox
    monkeypatch.chdir(tmp_path)

    data_root = tmp_path / "data"
    (data_root / "learning").mkdir(parents=True, exist_ok=True)
    (data_root / "feedback").mkdir(parents=True, exist_ok=True)

    # Prefer DATA_ROOT-aware modules, but CWD also protects any stragglers.
    monkeypatch.setenv("DATA_ROOT", str(data_root))

    # Ensure CAU has sane thresholds (and metrics exist)
    monkeypatch.setenv("CAU_S_MIN", "0.75")
    monkeypatch.setenv("CAU_H_MAX", "0.60")
    monkeypatch.setenv("CAU_DEFAULT_ALLOW_IF_NO_METRICS", "0")

    _write_dummy_ral_metrics(data_root)

    # Import AFTER env + chdir
    from backend.modules.aion_cognition.cee_exercise_playback import CEEPlayback

    pb = CEEPlayback(mode="simulate")
    summary = pb.run(n=3, feed="self_train")
    assert isinstance(summary, dict), "CEEPlayback.run() should return a summary dict"

    # ---- summary invariants ----
    assert summary.get("schema") == "CEEPlayback.v1"
    assert summary.get("self_state") is not None

    # ---- LexMemory artifact ----
    mem_path = data_root / "memory" / "lex_memory.json"
    assert mem_path.exists(), f"Missing {mem_path}"
    mem = json.loads(mem_path.read_text(encoding="utf-8") or "{}")
    assert isinstance(mem, dict) and len(mem) > 0, "lex_memory.json should be non-empty dict"

    # ---- Resonance history CSV ----
    hist_path = data_root / "telemetry" / "resonance_history.csv"
    assert hist_path.exists(), f"Missing {hist_path}"
    lines = [ln.strip() for ln in hist_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 2, "resonance_history.csv should have header + at least 1 data row"
    assert lines[0].split(",")[:5] == ["ts", "tag", "key", "SQI", "count"], "Unexpected CSV header"

    # ---- Resonance plot PNG ----
    img_path = data_root / "telemetry" / "resonance_trends.png"
    assert img_path.exists(), f"Missing {img_path}"
    assert img_path.stat().st_size > 0, "resonance_trends.png should be non-empty"