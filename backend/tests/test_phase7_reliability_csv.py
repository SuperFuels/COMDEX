import csv
import json
import os
import subprocess
import tempfile
from pathlib import Path


def test_phase7_reliability_csv_exists_and_sums_match():
    repo_root = Path(__file__).resolve().parents[2]
    run_demo = repo_root / "backend/demo/run_demo.py"
    demo_script = repo_root / "backend/demo/phase6_script.yaml"
    cal = repo_root / "backend/demo/phase7_calibration.py"

    assert run_demo.exists()
    assert demo_script.exists()
    assert cal.exists()

    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["DATA_ROOT"] = tmp
        env["PYTHONPATH"] = str(repo_root)
        env["PYTHONHASHSEED"] = "0"
        env["TZ"] = "UTC"
        env["LC_ALL"] = "C"

        subprocess.check_call(["python", str(run_demo), str(demo_script)], env=env, cwd=str(repo_root))
        subprocess.check_call(["python", str(cal)], env=env, cwd=str(repo_root))

        tel = Path(tmp) / "telemetry"
        csv_p = tel / "reliability_curve.csv"
        json_p = tel / "reliability_curve.json"

        assert csv_p.exists(), "Missing telemetry/reliability_curve.csv"
        assert json_p.exists(), "Missing telemetry/reliability_curve.json"

        curve = json.loads(json_p.read_text(encoding="utf-8"))
        n_samples = int(curve.get("n_samples") or 0)

        with open(csv_p, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 10, f"Expected 10 rows (bins), got {len(rows)}"

        summed = 0
        for r in rows:
            summed += int(r["n"])

        assert summed == n_samples, f"CSV n-sum {summed} != n_samples {n_samples}"