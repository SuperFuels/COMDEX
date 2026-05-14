from __future__ import annotations

import hashlib
from pathlib import Path

LOCK_SHA = Path("backend/tests/locks/v38_canonical_delta_determinism_replay_real_lock.sha256")
LOCK_OUT = Path("backend/tests/locks/v38_canonical_delta_determinism_replay_real_out.txt")
BENCH = Path("backend/tests/glyphos_wirepack_v38_canonical_delta_determinism_replay_real_benchmark.py")

def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def test_v38_real_lock_files_exist():
    assert BENCH.exists()
    assert LOCK_SHA.exists()
    assert LOCK_OUT.exists()

def test_v38_real_locks_match():
    exp = LOCK_SHA.read_text(encoding="utf-8").splitlines()
    exp = [ln.strip() for ln in exp if ln.strip() and not ln.strip().startswith("#")]

    # Expect two lines: <sha>  <filename>
    found = {}
    for ln in exp:
        parts = ln.split()
        if len(parts) < 2:
            continue
        sha = parts[0]
        fname = parts[-1]
        from pathlib import Path
        found[Path(fname).name] = sha

    assert BENCH.name in found, "lock file must include benchmark script"
    assert LOCK_OUT.name in found, "lock file must include out receipt"

    assert _sha256(BENCH) == found[BENCH.name]
    assert _sha256(LOCK_OUT) == found[LOCK_OUT.name]