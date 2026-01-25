import hashlib
import os
import subprocess
import tempfile
from pathlib import Path


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def test_phase7_outputs_are_deterministic_given_same_run():
    repo_root = Path(__file__).resolve().parents[2]
    phase7 = repo_root / "backend/demo/phase7_calibration.py"
    run_demo = repo_root / "backend/demo/run_demo.py"
    demo_script = repo_root / "backend/demo/phase6_script.yaml"

    assert phase7.exists()
    assert run_demo.exists()
    assert demo_script.exists()

    def run_once(tmpdir: str) -> tuple[str, str]:
        env = os.environ.copy()
        env["DATA_ROOT"] = tmpdir
        env["PYTHONPATH"] = str(repo_root)
        env["PYTHONHASHSEED"] = "0"
        env["TZ"] = "UTC"
        env["LC_ALL"] = "C"

        subprocess.check_call(["python", str(run_demo), str(demo_script)], env=env, cwd=str(repo_root))
        subprocess.check_call(["python", str(phase7)], env=env, cwd=str(repo_root))

        curve_p = Path(tmpdir) / "telemetry/reliability_curve.json"
        metrics_p = Path(tmpdir) / "telemetry/calibration_metrics.json"
        assert curve_p.exists()
        assert metrics_p.exists()
        return _sha256(curve_p), _sha256(metrics_p)

    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        sha_a = run_once(a)
        sha_b = run_once(b)
        assert sha_a == sha_b, f"Non-deterministic Phase7 outputs: {sha_a} != {sha_b}"