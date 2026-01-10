import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK_DIR = ROOT / "backend/tests/locks"

OUT = LOCK_DIR / "v43_multiwriter_merge_out.txt"
LOCK = LOCK_DIR / "v43_multiwriter_merge_lock.sha256"

BENCH = ROOT / "backend/tests/glyphos_wirepack_v43_multiwriter_merge_benchmark.py"
LEAN = ROOT / "backend/modules/lean/workspace/SymaticsBridge/V43_MultiWriterMergeNoMaterialization.lean"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_bench() -> str:
    r = subprocess.run(
        ["python", str(BENCH)],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
        env={**dict(**{"REQUIRE_LEAN": "1"}), **dict()},
    )
    return r.stdout


def test_v43_multiwriter_merge_locked():
    assert OUT.exists(), f"missing locked out: {OUT}"
    assert LOCK.exists(), f"missing lock sha: {LOCK}"

    out = run_bench()
    assert out == OUT.read_text(encoding="utf-8"), "benchmark output drifted"

    locked = LOCK.read_text(encoding="utf-8").strip().splitlines()
    assert len(locked) >= 2

    lean_sha = sha256_file(LEAN)
    out_sha = sha256_file(OUT)

    assert locked[0].startswith(lean_sha), "Lean file sha drifted"
    assert locked[1].startswith(out_sha), "locked out sha drifted"
