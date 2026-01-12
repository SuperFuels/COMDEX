from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK_DIR = ROOT / "backend/tests/locks"

OUT = LOCK_DIR / "v46_crosslang_vectors_out.txt"
LOCK = LOCK_DIR / "v46_crosslang_vectors_lock.sha256"

BENCH = ROOT / "backend/tests/glyphos_wirepack_v46_crosslang_vectors_benchmark.py"


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_v46_crosslang_vectors_locked() -> None:
    assert LOCK.exists(), f"missing lock sha: {LOCK}"
    assert OUT.exists(), f"missing locked out: {OUT}"

    locked = LOCK.read_text(encoding="utf-8").strip().splitlines()
    assert len(locked) == 2

    # Run benchmark in deterministic mode (no update)
    env = os.environ.copy()
    env["UPDATE_LOCKS"] = "0"
    env["REQUIRE_LEAN"] = env.get("REQUIRE_LEAN", "1")

    # Keep cross-lang checks off by default in CI unless explicitly enabled
    env.setdefault("VERIFY_RUST", "0")
    env.setdefault("VERIFY_GO", "0")
    env.setdefault("VERIFY_JS", "0")

    p = subprocess.run(
        ["python", str(BENCH)],
        cwd=str(ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    out = p.stdout
    assert out == OUT.read_text(encoding="utf-8"), "benchmark output drifted"

    out_sha = sha256_text(out)
    assert locked[1].startswith(out_sha), "locked out sha drifted"