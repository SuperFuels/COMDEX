import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCKDIR = ROOT / "backend" / "tests" / "locks"

LEAN = ROOT / "backend" / "modules" / "lean" / "workspace" / "SymaticsBridge" / "V36_CosineSimilarityNoMaterialization.lean"
OUT = LOCKDIR / "v36_cosine_similarity_no_materialization_out.txt"
LOCK = LOCKDIR / "v36_cosine_similarity_no_materialization_lock.sha256"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_lock_lines(text: str) -> dict:
    # sha256sum format: "<hash>  <path>"
    out = {}
    for line in text.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        out[parts[1]] = parts[0]
    return out


def test_v36_lock_files_exist():
    assert LEAN.exists(), f"missing: {LEAN}"
    assert OUT.exists(), f"missing: {OUT} (run benchmark + tee first)"
    assert LOCK.exists(), f"missing: {LOCK} (run sha256sum lock step)"


def test_v36_locks_match():
    lock_map = parse_lock_lines(LOCK.read_text(encoding="utf-8"))

    exp_lean = lock_map.get(str(LEAN), lock_map.get(LEAN.name))
    exp_out = lock_map.get(str(OUT), lock_map.get(OUT.name))
    assert exp_lean is not None, "lock file must include lean"
    assert exp_out is not None, "lock file must include out"

    got_lean = sha256_file(LEAN)
    got_out = sha256_file(OUT)

    assert got_lean == exp_lean
    assert got_out == exp_out