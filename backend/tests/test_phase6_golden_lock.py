import hashlib
import json
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


def test_phase6_golden_lock():
    """
    Phase 6 Golden Demo Lock

    Lock file format:
      {
        "schema": "AION.Phase6LockBundle.v1",
        "files": {
          "telemetry/demo_summary.lock.json": "<sha256>",
          "telemetry/forecast_report.lock.json": "<sha256>",
          ...
        }
      }
    """

    repo_root = Path(__file__).resolve().parents[2]
    demo_script = repo_root / "backend/demo/phase6_script.yaml"
    run_demo = repo_root / "backend/demo/run_demo.py"
    golden_lock_path = repo_root / "backend/tests/locks/phase6_lock_bundle.sha256.json"

    assert demo_script.exists()
    assert run_demo.exists()
    assert golden_lock_path.exists(), "Missing committed Phase 6 lock file"

    golden = json.loads(golden_lock_path.read_text(encoding="utf-8"))
    assert golden.get("schema") == "AION.Phase6LockBundle.v1"
    assert isinstance(golden.get("files"), dict) and golden["files"], "Golden lock 'files' missing/empty"

    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["DATA_ROOT"] = tmp
        env["PYTHONPATH"] = str(repo_root)

        subprocess.check_call(
            ["python", str(run_demo), str(demo_script)],
            env=env,
            cwd=str(repo_root),
        )

        produced_lock_path = Path(tmp) / "telemetry/phase6_lock_bundle.json"
        assert produced_lock_path.exists(), "Demo did not produce telemetry/phase6_lock_bundle.json"

        current = json.loads(produced_lock_path.read_text(encoding="utf-8"))
        assert current.get("schema") == "AION.Phase6LockBundle.v1"
        assert isinstance(current.get("files"), dict) and current["files"], "Produced lock 'files' missing/empty"

        # Compare keysets
        assert set(current["files"].keys()) == set(golden["files"].keys()), "Lock bundle file list changed"

        # Verify hashes
        for rel_path, expected_sha in golden["files"].items():
            p = Path(tmp) / rel_path
            assert p.exists(), f"Missing locked artifact: {rel_path}"
            actual_sha = sha256_file(p)
            assert actual_sha == expected_sha, f"Hash mismatch for {rel_path}"