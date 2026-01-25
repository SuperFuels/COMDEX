import hashlib
import os
import subprocess
import tempfile
from pathlib import Path


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def test_phase7_outputs_are_deterministic_given_same_run():
    repo_root = Path(__file__).resolve().parents[2]
    run_demo = repo_root / "backend/demo/run_demo.py"
    demo_script = repo_root / "backend/demo/phase6_script.yaml"
    phase7 = repo_root / "backend/demo/phase7_calibration.py"
    mk7 = repo_root / "backend/demo/make_phase7_lock_bundle.py"

    assert run_demo.exists(), run_demo
    assert demo_script.exists(), demo_script
    assert phase7.exists(), phase7
    assert mk7.exists(), mk7

    def run_once(tmpdir: str) -> tuple[str, str]:
        env = os.environ.copy()
        env["DATA_ROOT"] = tmpdir
        env["PYTHONPATH"] = str(repo_root)
        env["PYTHONHASHSEED"] = "0"
        env["TZ"] = "UTC"
        env["LC_ALL"] = "C"

        subprocess.check_call(["python", str(run_demo), str(demo_script)], env=env, cwd=str(repo_root))
        subprocess.check_call(["python", str(phase7)], env=env, cwd=str(repo_root))
        subprocess.check_call(["python", str(mk7)], env=env, cwd=str(repo_root))

        a = Path(tmpdir) / "telemetry/reliability_curve.lock.json"
        b = Path(tmpdir) / "telemetry/calibration_metrics.lock.json"
        assert a.exists(), a
        assert b.exists(), b
        return sha256_file(a), sha256_file(b)

    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        sha_a = run_once(t1)
        sha_b = run_once(t2)
        assert sha_a == sha_b, f"Non-deterministic Phase7 outputs: {sha_a} != {sha_b}"