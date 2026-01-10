from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK_DIR = ROOT / "backend/tests/locks"

OUT = LOCK_DIR / "v43_multiwriter_merge_out.txt"
LOCK = LOCK_DIR / "v43_multiwriter_merge_lock.sha256"
BENCH = ROOT / "backend/tests/glyphos_wirepack_v43_multiwriter_merge_benchmark.py"

LEAN_REL = "backend/modules/lean/workspace/SymaticsBridge/V43_MultiWriterMergeNoMaterialization.lean"
LEAN_FILE = ROOT / LEAN_REL


def run_bench() -> str:
    env = os.environ.copy()
    env["REQUIRE_LEAN"] = "1"
    r = subprocess.run(
        ["python", str(BENCH)],
        cwd=str(ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return r.stdout


def sha256_file(p: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_v43_multiwriter_merge_locked() -> None:
    assert LOCK.exists(), f"missing lock sha: {LOCK}"
    assert OUT.exists(), f"missing locked out: {OUT}"

    out = run_bench()
    assert out == OUT.read_text(encoding="utf-8"), "benchmark output drifted"

    lock_lines = LOCK.read_text(encoding="utf-8").strip().splitlines()
    assert len(lock_lines) >= 2

    lean_sha = sha256_file(LEAN_FILE)
    out_sha = sha256_file(OUT)

    assert lock_lines[0].startswith(lean_sha), "Lean file sha drifted"
    assert lock_lines[1].startswith(out_sha), "locked out sha drifted"
