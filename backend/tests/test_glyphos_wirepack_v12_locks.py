from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Keep this name aligned with the lock output you generated.
OUT_TXT = ROOT / "backend/tests/locks/glyphos_wirepack_v12_depth30_f8_m4096_r1_seed1337_skew0p8_out.txt"

# sha256sum backend/tests/locks/..._out.txt
EXPECTED_OUT_SHA256 = "2352c10f8fc74037cecc7a4a913736f0c0a56893e6acc164a31a505a9f34e11c"


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_v12_wirepack_lock_stdout_sha256() -> None:
    assert OUT_TXT.exists(), f"missing lock stdout file: {OUT_TXT}"
    got = _sha256_file(OUT_TXT)
    assert got == EXPECTED_OUT_SHA256, f"stdout lock changed: got={got} expected={EXPECTED_OUT_SHA256}"