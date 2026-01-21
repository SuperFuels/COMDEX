from __future__ import annotations

import hashlib
from pathlib import Path

LOCK_DIR = Path("backend/tests/locks")
OUT = LOCK_DIR / "glyphos_wirepack_v10_depth30_m2000_r1_seed1_out.txt"

# After you run the lock command, paste the printed sha256 here:
EXPECTED_OUT_SHA256 = "79dfafe8b6a373363821311e6870ac82a371fc254479d1ee8d8ad9b9cfd78bc7"


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_v10_wirepack_lock_stdout_sha256():
    assert OUT.exists(), f"Missing lock output: {OUT}"
    got = _sha256_file(OUT)
    assert got == EXPECTED_OUT_SHA256, f"stdout lock changed: got={got} expected={EXPECTED_OUT_SHA256}"