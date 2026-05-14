from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCKS = ROOT / "backend/tests/locks"

BENCH = ROOT / "backend/tests/glyphos_wirepack_v46_real_workload_replay_harness_benchmark.py"
OUT = LOCKS / "v46_real_workload_replay_harness_out.txt"
LOCK = LOCKS / "v46_real_workload_replay_harness_lock.sha256"


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_v46_real_workload_replay_harness_locked() -> None:
    env = os.environ.copy()
    env["REQUIRE_LEAN"] = "1"
    env.setdefault("UPDATE_LOCKS", "0")

    # run benchmark (stdout must match locked out file exactly)
    p = subprocess.run(
        ["python", str(BENCH)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    out = p.stdout

    assert OUT.exists(), f"missing locked out: {OUT}"
    assert out == OUT.read_text(encoding="utf-8"), "benchmark output drifted"

    # lock sha file must exist and match the out sha in line 2
    assert LOCK.exists(), f"missing lock sha: {LOCK}"
    locked = LOCK.read_text(encoding="utf-8").strip().splitlines()
    assert len(locked) >= 2, "lock sha must have at least 2 lines"

    out_sha = sha256_text(out)
    assert locked[1].startswith(out_sha), "locked out sha drifted"
