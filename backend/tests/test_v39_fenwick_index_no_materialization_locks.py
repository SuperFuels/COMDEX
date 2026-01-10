import os
import subprocess
import sys
from pathlib import Path
from difflib import unified_diff
import hashlib

ROOT = Path(__file__).resolve().parents[2]

BENCH = ROOT / "backend/tests/glyphos_wirepack_v39_fenwick_index_no_materialization_benchmark.py"
LOCK_OUT = ROOT / "backend/tests/locks/v39_fenwick_index_no_materialization_out.txt"
LOCK_SHA = ROOT / "backend/tests/locks/v39_fenwick_index_no_materialization_lock.sha256"


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _run_benchmark() -> bytes:
    r = subprocess.run(
        [sys.executable, str(BENCH)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if r.returncode != 0:
        raise AssertionError(
            "v39 benchmark failed.\n\n--- output ---\n"
            + r.stdout.decode("utf-8", errors="replace")
        )
    return r.stdout


def test_v39_lock_output_matches() -> None:
    out = _run_benchmark()

    update = os.environ.get("UPDATE_LOCKS", "").strip() == "1"
    if update:
        LOCK_OUT.parent.mkdir(parents=True, exist_ok=True)
        LOCK_OUT.write_bytes(out)
        # lock sha includes: sha256(lock_out_bytes) + sha256(script_bytes)
        sha_lines = [
            f"{_sha256_bytes(out)}  {LOCK_OUT.as_posix()}",
            f"{_sha256_bytes(BENCH.read_bytes())}  {BENCH.as_posix()}",
        ]
        LOCK_SHA.parent.mkdir(parents=True, exist_ok=True)
        LOCK_SHA.write_text("\n".join(sha_lines) + "\n", encoding="utf-8")
        return

    if not LOCK_OUT.exists():
        raise AssertionError(
            f"Missing lock output file: {LOCK_OUT}\n\n"
            "Generate it with:\n"
            f"  UPDATE_LOCKS=1 {sys.executable} -m pytest -q {__file__}\n"
            "or run the benchmark and redirect stdout into the lock file."
        )

    expected = LOCK_OUT.read_bytes()
    if out != expected:
        diff = "\n".join(
            unified_diff(
                expected.decode("utf-8", errors="replace").splitlines(),
                out.decode("utf-8", errors="replace").splitlines(),
                fromfile=str(LOCK_OUT),
                tofile="(current)",
                lineterm="",
            )
        )
        raise AssertionError("v39 lock output mismatch:\n\n" + diff)

    # optional: validate sha lock file exists + matches
    if not LOCK_SHA.exists():
        raise AssertionError(
            f"Missing lock sha file: {LOCK_SHA}\n\n"
            "Generate it with:\n"
            f"  UPDATE_LOCKS=1 {sys.executable} -m pytest -q {__file__}\n"
        )

    sha_expected_lines = [
        f"{_sha256_bytes(expected)}  {LOCK_OUT.as_posix()}",
        f"{_sha256_bytes(BENCH.read_bytes())}  {BENCH.as_posix()}",
    ]
    sha_expected = "\n".join(sha_expected_lines) + "\n"
    sha_actual = LOCK_SHA.read_text(encoding="utf-8")

    if sha_actual != sha_expected:
        raise AssertionError(
            "v39 sha lock mismatch.\n\nExpected:\n"
            + sha_expected
            + "\nActual:\n"
            + sha_actual
        )