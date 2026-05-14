from __future__ import annotations

import hashlib
from pathlib import Path

LOCK_DIR = Path("backend/tests/locks")

LOCKS = [
    "glyphos_compression_depth30_lock.sha256",
    "glyphos_compression_depth45_lock.sha256",
    "glyphos_compression_depth60_lock.sha256",
]

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _parse_lock(lock_path: Path) -> dict[str, str]:
    # format: "<hex>  <path>"
    out: dict[str, str] = {}
    for line in lock_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        hexd, rel = line.split(None, 1)
        rel = rel.strip()
        out[rel] = hexd
    return out

def test_glyphos_compression_locks_present() -> None:
    for name in LOCKS:
        p = LOCK_DIR / name
        assert p.exists(), f"missing lock file: {p}"

def test_glyphos_compression_lock_hashes_match() -> None:
    for name in LOCKS:
        lock_path = LOCK_DIR / name
        expected = _parse_lock(lock_path)

        for rel, hex_expected in expected.items():
            file_path = Path(rel)
            assert file_path.exists(), f"missing referenced file: {file_path} (from {lock_path})"
            hex_actual = _sha256_file(file_path)
            assert hex_actual == hex_expected, (
                f"hash mismatch in {lock_path} for {rel}\n"
                f"expected {hex_expected}\n"
                f"actual   {hex_actual}"
            )
