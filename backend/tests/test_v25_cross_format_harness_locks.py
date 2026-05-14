import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BENCH_FILE = ROOT / "backend/tests/glyphos_wirepack_v25_cross_format_harness_benchmark.py"
OUT_FILE = ROOT / "backend/tests/locks/v25_cross_format_out.txt"
LOCK_FILE = ROOT / "backend/tests/locks/v25_cross_format_lock.sha256"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def test_v25_benchmark_smoke_runs():
    # Small smoke run so CI proves the harness executes.
    subprocess.run(
        [
            "python",
            rel(BENCH_FILE),
            "--seed",
            "25025",
            "--depth",
            "16",
            "--headers",
            "8",
            "--n",
            "32",
            "--muts",
            "1",
        ],
        cwd=str(ROOT),
        check=True,
    )


def test_v25_lock_hashes_match():
    assert BENCH_FILE.exists(), f"missing {BENCH_FILE}"
    assert OUT_FILE.exists(), f"missing {OUT_FILE}"
    assert LOCK_FILE.exists(), f"missing {LOCK_FILE}"

    want = LOCK_FILE.read_text(encoding="utf-8").strip().splitlines()
    got = [
        f"{sha256_file(BENCH_FILE)}  {rel(BENCH_FILE)}",
        f"{sha256_file(OUT_FILE)}  {rel(OUT_FILE)}",
    ]
    assert want == got