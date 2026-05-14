from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BENCH = ROOT / "backend/tests/glyphos_wirepack_v44_sql_subset_translation_benchmark.py"
OUT = ROOT / "backend/tests/locks/v44_sql_subset_translation_out.txt"
LOCK = ROOT / "backend/tests/locks/v44_sql_subset_translation_lock.sha256"
LEAN = ROOT / "backend/modules/lean/workspace/SymaticsBridge/V44_SQLSubsetTranslationNoMaterialization.lean"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_bench() -> str:
    env = os.environ.copy()
    env["REQUIRE_LEAN"] = "1"
    env["UPDATE_LOCKS"] = "0"
    # keep Lean output quiet; benchmark already suppresses Lean logs unless PRINT_LEAN_LOG=1
    r = subprocess.run(
        ["python", str(BENCH)],
        cwd=str(ROOT),
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    return r.stdout


def test_v44_sql_subset_translation_locked() -> None:
    assert OUT.exists(), f"missing out file: {OUT}"
    assert LOCK.exists(), f"missing lock sha: {LOCK}"
    assert LEAN.exists(), f"missing Lean file: {LEAN}"
    assert BENCH.exists(), f"missing bench: {BENCH}"

    out = run_bench()
    assert out == OUT.read_text(encoding="utf-8"), "benchmark output drifted"

    locked = LOCK.read_text(encoding="utf-8").strip().splitlines()
    assert len(locked) >= 2, "lock file must have 2 lines (lean sha + out sha)"

    lean_sha = sha256_file(LEAN)
    out_sha = sha256_file(OUT)

    assert locked[0].startswith(lean_sha), "Lean file sha drifted"
    assert locked[1].startswith(out_sha), "locked out sha drifted"