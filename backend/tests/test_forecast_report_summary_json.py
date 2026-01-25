from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_forecast_report_summary_json(tmp_path: Path):
    env = os.environ.copy()
    env["DATA_ROOT"] = str(tmp_path)
    env["PYTHONPATH"] = str(Path.cwd())
    env["AION_COMMENTARY"] = "0"
    env["AION_VERBOSITY"] = "minimal"

    # force prediction_miss + risk emission
    env["AION_FORECAST_MIN_CONF"] = "0.1"
    env["AION_FORECAST_RHO_ERR"] = "0.05"
    env["AION_FORECAST_SQI_ERR"] = "0.05"
    env["AION_RISK_MIN_CONF"] = "0.1"
    env["AION_RISK_MIN_SCORE"] = "0.0"

    cmd = [
        sys.executable,
        "backend/modules/aion_cognition/cee_exercise_playback.py",
        "--n",
        "6",
    ]
    subprocess.check_call(cmd, env=env)

    outp = tmp_path / "telemetry" / "forecast_report.json"
    assert outp.exists(), f"missing {outp}"

    data = json.loads(outp.read_text(encoding="utf-8"))
    assert data.get("schema") == "AION.ForecastReport.v1"
    assert isinstance(data.get("session"), str) and data["session"].startswith("PLAY-")
    assert int(data.get("n_forecasts") or 0) >= 1
    assert int(data.get("n_prediction_miss") or 0) >= 1  # with forced low thresholds