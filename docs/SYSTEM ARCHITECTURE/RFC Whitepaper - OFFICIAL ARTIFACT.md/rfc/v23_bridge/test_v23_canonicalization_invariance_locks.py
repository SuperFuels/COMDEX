import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LEAN_FILE = ROOT / "backend/modules/lean/workspace/SymaticsBridge/CanonicalizationInvariance.lean"
OUT_FILE = ROOT / "backend/tests/locks/v23_canon_invariance_out.txt"
LOCK_FILE = ROOT / "backend/tests/locks/v23_canon_invariance_lock.sha256"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()

def test_v23_lean_verifies():
    subprocess.run(
        ["lake", "env", "lean", "SymaticsBridge/CanonicalizationInvariance.lean"],
        cwd=str(ROOT / "backend/modules/lean/workspace"),
        check=True,
    )

def test_v23_lock_hashes_match():
    assert LEAN_FILE.exists(), f"missing {LEAN_FILE}"
    assert OUT_FILE.exists(), f"missing {OUT_FILE}"
    assert LOCK_FILE.exists(), f"missing {LOCK_FILE}"

    want = LOCK_FILE.read_text(encoding="utf-8").strip().splitlines()
    got = [
        f"{sha256_file(LEAN_FILE)}  {rel(LEAN_FILE)}",
        f"{sha256_file(OUT_FILE)}  {rel(OUT_FILE)}",
    ]
    assert want == got