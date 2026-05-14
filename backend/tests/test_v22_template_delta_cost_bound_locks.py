import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LEAN_FILE = ROOT / "backend/modules/lean/workspace/SymaticsBridge/TemplateDeltaCostBound.lean"
OUT_FILE = ROOT / "backend/tests/locks/v22_template_delta_out.txt"
LOCK_FILE = ROOT / "backend/tests/locks/v22_template_delta_lock.sha256"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def test_v22_lean_verifies():
    subprocess.run(
        ["lake", "env", "lean", "SymaticsBridge/TemplateDeltaCostBound.lean"],
        cwd=str(ROOT / "backend/modules/lean/workspace"),
        check=True,
    )


def test_v22_lock_hashes_match():
    assert LEAN_FILE.exists(), f"missing {LEAN_FILE}"
    assert OUT_FILE.exists(), f"missing {OUT_FILE}"
    assert LOCK_FILE.exists(), f"missing {LOCK_FILE}"

    # IMPORTANT: match sha256sum output style used by the lock file (relative paths)
    got = [
        f"{sha256_file(LEAN_FILE)}  backend/modules/lean/workspace/SymaticsBridge/TemplateDeltaCostBound.lean",
        f"{sha256_file(OUT_FILE)}  backend/tests/locks/v22_template_delta_out.txt",
    ]
    want = LOCK_FILE.read_text(encoding="utf-8").strip().splitlines()
    assert want == got