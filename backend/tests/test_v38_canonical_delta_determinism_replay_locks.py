from __future__ import annotations

import os
import hashlib

LOCK_PATH = "backend/tests/locks/v38_canonical_delta_determinism_replay_lock.sha256"

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _parse_lock(lock_path: str) -> dict[str, str]:
    """
    Expects:
      <sha256>  <BASENAME>
    """
    out: dict[str, str] = {}
    with open(lock_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            sha, base = parts
            out[base] = sha
    return out

def test_v38_lock_file_present():
    assert os.path.exists(LOCK_PATH), f"missing lock file: {LOCK_PATH}"

def test_v38_locks_match():
    locks = _parse_lock(LOCK_PATH)

    exp_lean = locks.get("V38_CanonicalDeltaDeterminismReplay.lean")
    exp_out  = locks.get("v38_canonical_delta_determinism_replay_out.txt")

    assert exp_lean is not None, "lock file must include lean"
    assert exp_out  is not None, "lock file must include output"

    lean_path = "backend/modules/lean/workspace/SymaticsBridge/V38_CanonicalDeltaDeterminismReplay.lean"
    out_path  = "backend/tests/locks/v38_canonical_delta_determinism_replay_out.txt"

    assert os.path.exists(lean_path), f"missing lean artifact: {lean_path}"
    assert os.path.exists(out_path),  f"missing benchmark output: {out_path}"

    got_lean = _sha256_file(lean_path)
    got_out  = _sha256_file(out_path)

    assert got_lean == exp_lean, f"lean sha mismatch: expected {exp_lean}, got {got_lean}"
    assert got_out  == exp_out,  f"out sha mismatch: expected {exp_out}, got {got_out}"
