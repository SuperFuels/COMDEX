from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BENCH = ROOT / "backend/tests/glyphos_wirepack_v42_incremental_merkle_commitment_benchmark.py"
LEAN = ROOT / "backend/modules/lean/workspace/SymaticsBridge/V42_IncrementalMerkleCommitment.lean"

LOCK_DIR = ROOT / "backend/tests/locks"
OUT = LOCK_DIR / "v42_incremental_merkle_commitment_out.txt"
LOCK = LOCK_DIR / "v42_incremental_merkle_commitment_lock.sha256"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_bench() -> str:
    env = os.environ.copy()
    env["REQUIRE_LEAN"] = "1"
    r = subprocess.run(
        ["python", str(BENCH)],
        cwd=str(ROOT),
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return r.stdout


def test_v42_incremental_merkle_commitment_locked() -> None:
    assert LEAN.exists(), f"missing Lean file: {LEAN}"
    assert LOCK.exists(), f"missing lock sha: {LOCK}"
    assert OUT.exists(), f"missing locked out: {OUT}"

    out = run_bench()
    # keep the out file as the canonical human-auditable artifact
    assert out == OUT.read_text(encoding="utf-8"), "benchmark output drifted"

    lean_sha = sha256_file(LEAN)
    out_sha = sha256_file(OUT)

    locked = LOCK.read_text(encoding="utf-8").strip().splitlines()
    assert len(locked) >= 2, "lock sha file must have at least 2 lines"

    assert locked[0].startswith(lean_sha), "Lean file sha drifted"
    assert "backend/modules/lean/workspace/SymaticsBridge/V42_IncrementalMerkleCommitment.lean" in locked[0]

    assert locked[1].startswith(out_sha), "locked out sha drifted"
    assert "backend/tests/locks/v42_incremental_merkle_commitment_out.txt" in locked[1]
