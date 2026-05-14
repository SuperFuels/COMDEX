# backend/tests/test_v40_correlation_two_streams_locks.py
"""
Lock/regression test for:
  v40 — Correlation over two delta streams (no materialization)

Policy:
- Runs the benchmark as a subprocess (so output format is locked).
- Requires Lean to compile (REQUIRE_LEAN=1).
- Verifies:
    (a) output matches backend/tests/locks/v40_correlation_two_streams_out.txt
    (b) lock sha256 lines match backend/tests/locks/v40_correlation_two_streams_lock.sha256
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

BENCH = ROOT / "backend/tests/glyphos_wirepack_v40_correlation_two_streams_no_materialization_benchmark.py"
LOCK_OUT = ROOT / "backend/tests/locks/v40_correlation_two_streams_out.txt"
LOCK_SHA = ROOT / "backend/tests/locks/v40_correlation_two_streams_lock.sha256"


def _run_bench() -> str:
    env = dict(os.environ)
    env["REQUIRE_LEAN"] = "1"

    p = subprocess.run(
        ["python", str(BENCH)],
        cwd=str(ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    return p.stdout


def _read_lock_lines(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").splitlines()


def _extract_sha_lines(out: str) -> list[str]:
    """
    Extract the two SHA256 lines printed under:
      SHA256 (v40)
    Example line format:
      <hex>  /abs/path/to/file
    """
    lines = out.splitlines()
    try:
        i = lines.index("SHA256 (v40)")
    except ValueError:
        raise AssertionError("Missing 'SHA256 (v40)' marker in output")

    # scan forward for sha lines
    sha_pat = re.compile(r"^[0-9a-f]{64}\s{2}/.+$")
    sha_lines: list[str] = []
    for ln in lines[i + 1 :]:
        if sha_pat.match(ln.strip()):
            sha_lines.append(ln.strip())
        # stop early if we already got both
        if len(sha_lines) >= 2:
            break

    if len(sha_lines) != 2:
        raise AssertionError(f"Expected 2 sha lines, got {len(sha_lines)}: {sha_lines}")
    return sha_lines


def _extract_lean_ok(out: str) -> int:
    m = re.search(r"\bLEAN_OK=(\d)\b", out)
    if not m:
        raise AssertionError("Missing LEAN_OK=... in output")
    return int(m.group(1))


def _extract_drift_sha(out: str) -> str:
    m = re.search(r"\bdrift_sha256=([0-9a-f]{64})\b", out)
    if not m:
        raise AssertionError("Missing drift_sha256=... in output")
    return m.group(1)


def test_v40_correlation_two_streams_locks() -> None:
    assert BENCH.exists(), f"missing benchmark: {BENCH}"
    assert LOCK_OUT.exists(), f"missing lock output: {LOCK_OUT}"
    assert LOCK_SHA.exists(), f"missing lock sha file: {LOCK_SHA}"

    out = _run_bench()

    # must compile Lean
    assert _extract_lean_ok(out) == 1

    # locked stdout match (strongest regression)
    expected = LOCK_OUT.read_text(encoding="utf-8")
    assert out == expected, "Benchmark stdout changed; update locks if intentional."

    # lock sha lines: file sha256 + path (2 lines)
    sha_lines = _extract_sha_lines(out)
    lock_lines = [ln.strip() for ln in _read_lock_lines(LOCK_SHA) if ln.strip()]
    assert len(lock_lines) >= 2, f"lock sha file must have >=2 lines: {LOCK_SHA}"

    # compare first 2 non-empty lock lines to emitted sha lines
    assert sha_lines[0] == lock_lines[0], "Lean file sha/path mismatch vs lock"
    assert sha_lines[1] == lock_lines[1], "Benchmark file sha/path mismatch vs lock"

    # optional: ensure drift hash appears and stays locked via stdout equality above
    _ = _extract_drift_sha(out)