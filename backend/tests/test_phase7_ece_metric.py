import json
import os
import subprocess
import tempfile
from pathlib import Path


def test_phase7_ece_is_bounded_and_consistent():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "backend/demo/phase7_calibration.py"
    assert script.exists(), "Missing backend/demo/phase7_calibration.py"

    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["DATA_ROOT"] = tmp
        env["PYTHONPATH"] = str(repo_root)
        env["PYTHONHASHSEED"] = "0"
        env["TZ"] = "UTC"
        env["LC_ALL"] = "C"

        run_demo = repo_root / "backend/demo/run_demo.py"
        demo_script = repo_root / "backend/demo/phase6_script.yaml"
        subprocess.check_call(["python", str(run_demo), str(demo_script)], env=env, cwd=str(repo_root))

        subprocess.check_call(["python", str(script)], env=env, cwd=str(repo_root))

        metrics_p = Path(tmp) / "telemetry/calibration_metrics.json"
        curve_p = Path(tmp) / "telemetry/reliability_curve.json"
        assert metrics_p.exists()
        assert curve_p.exists()

        metrics = json.loads(metrics_p.read_text(encoding="utf-8"))
        assert metrics.get("schema") == "AION.CalibrationMetrics.v1"

        ece = metrics.get("ece")
        assert isinstance(ece, (int, float))
        ece = float(ece)
        assert 0.0 <= ece <= 1.0, f"ECE out of bounds: {ece}"

        # Consistency: n_samples should match curve
        curve = json.loads(curve_p.read_text(encoding="utf-8"))
        assert metrics.get("n_samples") == curve.get("n_samples")
        assert metrics.get("n_bins") == 10