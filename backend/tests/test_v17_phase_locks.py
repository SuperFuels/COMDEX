import hashlib
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # backend/tests/.. -> repo root

LEAN_WORKSPACE = REPO / "backend/modules/lean/workspace"
LEAN_FILE = LEAN_WORKSPACE / "SymaticsBridge/PhaseInterferenceBloat.lean"

BENCH = REPO / "backend/tests/glyphos_wirepack_v17_phase_interference_bloat_benchmark.py"
LOCK_DIR = REPO / "backend/tests/locks"
LOCK_OUT = LOCK_DIR / "v17_phase_out.txt"
LOCK_SHA = LOCK_DIR / "v17_phase_lock.sha256"


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def test_v17_lean_verifies():
    # Lean should exit non-zero on any error.
    subprocess.run(
        ["lake", "env", "lean", str(LEAN_FILE.relative_to(LEAN_WORKSPACE))],
        cwd=str(LEAN_WORKSPACE),
        check=True,
    )


def test_v17_benchmark_output_locked():
    assert LOCK_OUT.exists(), f"Missing lock output: {LOCK_OUT}"
    proc = subprocess.run(
        ["python", str(BENCH)],
        cwd=str(REPO),
        check=True,
        capture_output=True,
        text=True,
    )
    got = proc.stdout.replace("\r\n", "\n")
    expected = LOCK_OUT.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert got == expected, (
        "v17 benchmark output drifted.\n"
        "If this is intentional, regenerate locks:\n"
        "  python backend/tests/glyphos_wirepack_v17_phase_interference_bloat_benchmark.py | tee backend/tests/locks/v17_phase_out.txt\n"
        "  sha256sum backend/modules/lean/workspace/SymaticsBridge/PhaseInterferenceBloat.lean backend/tests/locks/v17_phase_out.txt | tee backend/tests/locks/v17_phase_lock.sha256\n"
    )


def test_v17_lock_sha256_matches():
    assert LOCK_SHA.exists(), f"Missing lock sha: {LOCK_SHA}"

    lean_hash = sha256_file(LEAN_FILE)
    out_hash = sha256_file(LOCK_OUT)

    # Normalize lock file parsing: "<hash><space><space><path>"
    lines = [ln.strip() for ln in LOCK_SHA.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2, "Lock sha file should have exactly 2 lines (Lean file + bench output)."

    exp1_hash, exp1_path = lines[0].split(maxsplit=1)
    exp2_hash, exp2_path = lines[1].split(maxsplit=1)

    assert exp1_path.endswith(str(LEAN_FILE.relative_to(REPO))), f"Unexpected path in lock: {exp1_path}"
    assert exp2_path.endswith(str(LOCK_OUT.relative_to(REPO))), f"Unexpected path in lock: {exp2_path}"

    assert exp1_hash == lean_hash, "Lean file sha changed (update locks if intentional)."
    assert exp2_hash == out_hash, "Benchmark output sha changed (update locks if intentional)."