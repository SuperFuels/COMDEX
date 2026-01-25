import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(p: Path) -> Dict[str, Any]:
    obj = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(obj, dict), f"Expected dict JSON in {p}"
    return obj


def test_phase7_golden_lock():
    repo_root = Path(__file__).resolve().parents[2]

    run_demo = repo_root / "backend/demo/run_demo.py"
    demo_script = repo_root / "backend/demo/phase6_script.yaml"
    phase7 = repo_root / "backend/demo/phase7_calibration.py"
    mk7 = repo_root / "backend/demo/make_phase7_lock_bundle.py"
    golden_lock_path = repo_root / "backend/tests/locks/phase7_lock_bundle.sha256.json"

    # Sanity: inputs exist
    assert run_demo.exists(), run_demo
    assert demo_script.exists(), demo_script
    assert phase7.exists(), phase7
    assert mk7.exists(), mk7
    assert golden_lock_path.exists(), f"Missing committed Phase 7 lock file: {golden_lock_path}"

    # Load golden
    golden = read_json(golden_lock_path)
    assert golden.get("schema") == "AION.Phase7LockBundle.v2"
    assert isinstance(golden.get("files"), dict) and golden["files"], "Golden lock has no files map"

    expected_keys = {
        "telemetry/reliability_curve.lock.json",
        "telemetry/calibration_metrics.lock.json",
    }
    assert set(golden["files"].keys()) == expected_keys, f"Unexpected golden keys: {sorted(golden['files'].keys())}"

    # Helpful debug: show exactly which file pytest is reading
    print(f"[PHASE7_TEST] repo_root={repo_root}")
    print(f"[PHASE7_TEST] golden_lock_path={golden_lock_path}")
    print(f"[PHASE7_TEST] golden_files={sorted(golden['files'].keys())}")

    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["DATA_ROOT"] = tmp
        env["PYTHONPATH"] = str(repo_root)
        env["PYTHONHASHSEED"] = "0"
        env["TZ"] = "UTC"
        env["LC_ALL"] = "C"

        # Phase 6 demo (generates telemetry inputs)
        subprocess.check_call(["python", str(run_demo), str(demo_script)], env=env, cwd=str(repo_root))

        # Phase 7 analysis (generates raw reliability_curve + metrics)
        subprocess.check_call(["python", str(phase7)], env=env, cwd=str(repo_root))

        # Sanity: required raw Phase7 artifacts exist BEFORE locking
        raw_req = [
            Path(tmp) / "telemetry/reliability_curve.json",
            Path(tmp) / "telemetry/calibration_metrics.json",
        ]
        for p in raw_req:
            assert p.exists(), f"Missing Phase7 artifact before locking: {p}"

        # Create lock bundle (writes *.lock.json + phase7_lock_bundle.json)
        subprocess.check_call(["python", str(mk7)], env=env, cwd=str(repo_root))

        produced_bundle = Path(tmp) / "telemetry/phase7_lock_bundle.json"
        assert produced_bundle.exists(), f"Missing produced bundle: {produced_bundle}"

        current = read_json(produced_bundle)
        assert current.get("schema") == "AION.Phase7LockBundle.v2"
        assert isinstance(current.get("files"), dict) and current["files"], "Produced bundle has no files map"

        # Keys must match exactly (no drift)
        gkeys = set(golden["files"].keys())
        ckeys = set(current["files"].keys())
        assert ckeys == gkeys, (
            "Locked file list changed.\n"
            f"missing={sorted(gkeys-ckeys)}\n"
            f"extra={sorted(ckeys-gkeys)}"
        )

        # Compare hashes against the actual files on disk (not the bundle values)
        mismatches = []
        for rel_path, expected_sha in golden["files"].items():
            p = Path(tmp) / rel_path
            assert p.exists(), f"Missing locked artifact: {rel_path}"
            actual_sha = sha256_file(p)
            if actual_sha != expected_sha:
                mismatches.append((rel_path, expected_sha, actual_sha))

        if mismatches:
            lines = ["Hash mismatches:"]
            for rel_path, exp, act in mismatches:
                lines.append(f"  - {rel_path}\n      expected={exp}\n      actual  ={act}")
            raise AssertionError("\n".join(lines))