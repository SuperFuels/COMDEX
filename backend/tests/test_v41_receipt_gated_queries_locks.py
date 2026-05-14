import os
import subprocess
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[2]

BENCH = ROOT / "backend/tests/glyphos_wirepack_v41_receipt_gated_queries_benchmark.py"
LOCK_DIR = ROOT / "backend/tests/locks"
OUT = LOCK_DIR / "v41_receipt_gated_queries_out.txt"
LOCK = LOCK_DIR / "v41_receipt_gated_queries_lock.sha256"

LEAN_FILE = ROOT / "backend/modules/lean/workspace/SymaticsBridge/V41_ReceiptGatedQueries.lean"

UPDATE_LOCKS = os.environ.get("UPDATE_LOCKS", "0") == "1"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_bench() -> str:
    env = os.environ.copy()
    env.setdefault("REQUIRE_LEAN", "1")
    r = subprocess.run(
        ["python", str(BENCH)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    return r.stdout


def test_v41_receipt_gated_queries_locked():
    LOCK_DIR.mkdir(parents=True, exist_ok=True)

    out = run_bench()
    assert "LEAN_OK=1" in out, "Lean must compile for v41 (set REQUIRE_LEAN=1)"

    lean_sha = sha256_file(LEAN_FILE)

    if UPDATE_LOCKS or (not OUT.exists()) or (not LOCK.exists()):
        OUT.write_text(out, encoding="utf-8")
        LOCK.write_text(
            f"{lean_sha}  {LEAN_FILE.as_posix()}\n"
            f"{sha256_file(OUT)}  {OUT.as_posix()}\n",
            encoding="utf-8",
        )
        return

    # exact output match
    locked_out = OUT.read_text(encoding="utf-8")
    assert out == locked_out, "v41 output drifted vs lock"

    # sha match
    locked_sha = LOCK.read_text(encoding="utf-8").strip().splitlines()
    assert locked_sha[0].startswith(lean_sha), "Lean file sha drifted"
    assert locked_sha[1].startswith(sha256_file(OUT)), "out.txt sha drifted"
