# backend/tests/test_risk_awareness_log_jsonl.py
from __future__ import annotations

import json
import subprocess
import sys


def test_risk_awareness_log_jsonl(tmp_path, monkeypatch):
    # isolate artifacts
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))

    # force emission even with low confidence / missing S/H
    monkeypatch.setenv("AION_RISK_MIN_CONF", "0.1")
    monkeypatch.setenv("AION_RISK_MIN_SCORE", "0.0")

    # keep noise low, but ok either way
    monkeypatch.setenv("AION_COMMENTARY", "0")
    monkeypatch.setenv("AION_VERBOSITY", "off")

    cmd = [
        sys.executable,
        "backend/modules/aion_cognition/cee_exercise_playback.py",
        "--n",
        "3",
    ]

    r = subprocess.run(
        cmd,
        cwd=".",
        capture_output=True,
        text=True,
        env={**dict(**__import__("os").environ), "PYTHONPATH": "."},
    )
    assert r.returncode == 0, f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"

    p = tmp_path / "telemetry" / "risk_awareness_log.jsonl"
    assert p.exists(), f"missing {p}.\nls:\n{list(tmp_path.rglob('*'))}"

    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1

    ok = False
    for ln in lines:
        rec = json.loads(ln)
        if rec.get("schema") == "AION.RiskAwareness.v1":
            ok = True
            break
    assert ok, f"no AION.RiskAwareness.v1 record found in:\n{lines}"