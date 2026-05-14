from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCK_DIR = ROOT / "backend" / "tests" / "locks"
LOCK_DIR.mkdir(parents=True, exist_ok=True)

OUT_TXT = LOCK_DIR / "v38_projection_query_no_materialization_out.txt"
LOCK_SHA = LOCK_DIR / "v38_projection_query_no_materialization_lock.sha256"
LEAN_FILE = ROOT / "backend" / "modules" / "lean" / "workspace" / "SymaticsBridge" / "V38_ProjectionQueryNoMaterialization.lean"

def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def test_v38_projection_query_no_materialization_locks():
    # run benchmark
    cmd = [sys.executable, str(ROOT / "backend" / "tests" / "glyphos_wirepack_v38_projection_query_no_materialization_benchmark.py")]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, f"benchmark failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"

    OUT_TXT.write_text(r.stdout, encoding="utf-8")

    assert LEAN_FILE.exists(), f"missing lean bridge file: {LEAN_FILE}"

    lock_text = (
        f"{_sha256_file(LEAN_FILE)}  {LEAN_FILE.name}\n"
        f"{_sha256_file(OUT_TXT)}  {OUT_TXT.name}\n"
    )

    # If lock exists, enforce; else create
    if LOCK_SHA.exists():
        expected = LOCK_SHA.read_text(encoding="utf-8")
        assert lock_text == expected, f"lock mismatch:\n---expected---\n{expected}\n---got---\n{lock_text}"
    else:
        LOCK_SHA.write_text(lock_text, encoding="utf-8")