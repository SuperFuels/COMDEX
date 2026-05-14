import json
import os
import subprocess
import tempfile
from pathlib import Path


def test_phase7_bins_sum_to_total_and_schema_ok():
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

        # Run Phase 6 demo first to produce telemetry into DATA_ROOT
        run_demo = repo_root / "backend/demo/run_demo.py"
        demo_script = repo_root / "backend/demo/phase6_script.yaml"
        subprocess.check_call(["python", str(run_demo), str(demo_script)], env=env, cwd=str(repo_root))

        # Now run Phase 7 calibration (read-only)
        subprocess.check_call(["python", str(script)], env=env, cwd=str(repo_root))

        curve_p = Path(tmp) / "telemetry/reliability_curve.json"
        metrics_p = Path(tmp) / "telemetry/calibration_metrics.json"
        assert curve_p.exists(), "Missing telemetry/reliability_curve.json"
        assert metrics_p.exists(), "Missing telemetry/calibration_metrics.json"

        curve = json.loads(curve_p.read_text(encoding="utf-8"))
        assert curve.get("schema") == "AION.ReliabilityCurve.v1"

        bins = curve.get("bins")
        assert isinstance(bins, list) and len(bins) == 10, "Expected 10 bins"

        total = curve.get("n_samples")
        assert isinstance(total, int) and total >= 0

        summed = 0
        for b in bins:
            assert isinstance(b, dict)
            assert "bin" in b
            assert "n" in b
            assert "avg_conf" in b
            assert "emp_acc" in b
            summed += int(b.get("n", 0))

            # numeric sanity
            if b.get("avg_conf") is not None:
                assert 0.0 <= float(b["avg_conf"]) <= 1.0
            if b.get("emp_acc") is not None:
                assert 0.0 <= float(b["emp_acc"]) <= 1.0

        assert summed == total, f"Bin counts sum {summed} != total {total}"