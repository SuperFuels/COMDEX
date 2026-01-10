from __future__ import annotations

from pathlib import Path
import hashlib


ROOT = Path(__file__).resolve().parents[2]  # /workspaces/COMDEX
LOCK = ROOT / "backend/tests/locks/v38_canonical_delta_determinism_replay_wirepack_lock.sha256"
BENCH = ROOT / "backend/tests/glyphos_wirepack_v38_canonical_delta_determinism_replay_wirepack_benchmark.py"
OUT = ROOT / "backend/tests/locks/v38_canonical_delta_determinism_replay_wirepack_out.txt"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_lock(lock_path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in lock_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            digest = parts[0]
            relpath = parts[1]
            found[relpath] = digest
    return found


def test_v38_wirepack_lock_files_exist() -> None:
    assert BENCH.exists(), f"missing benchmark: {BENCH}"
    assert OUT.exists(), f"missing output: {OUT}"
    assert LOCK.exists(), f"missing lock file: {LOCK}"


def test_v38_wirepack_locks_match() -> None:
    found = _parse_lock(LOCK)

    # lock file is written with these exact paths (see your sha256sum command)
    bench_key = "backend/tests/glyphos_wirepack_v38_canonical_delta_determinism_replay_wirepack_benchmark.py"
    out_key = "backend/tests/locks/v38_canonical_delta_determinism_replay_wirepack_out.txt"

    assert bench_key in found and out_key in found, "lock must include benchmark + out"

    assert found[bench_key] == _sha256(BENCH)
    assert found[out_key] == _sha256(OUT)