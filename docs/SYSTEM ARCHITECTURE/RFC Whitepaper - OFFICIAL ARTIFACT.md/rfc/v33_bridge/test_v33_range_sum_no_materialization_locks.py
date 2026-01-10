import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCKDIR = ROOT / "backend" / "tests" / "locks"

LEAN = ROOT / "backend" / "modules" / "lean" / "workspace" / "SymaticsBridge" / "V33_RangeSumNoMaterialization.lean"
OUT = LOCKDIR / "v33_range_sum_no_materialization_out.txt"
LOCK = LOCKDIR / "v33_range_sum_no_materialization_lock.sha256"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_lock_lines(text: str) -> dict:
    out = {}
    for line in text.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        h, p = parts[0], parts[1]
        out[p] = h
        out[Path(p).name] = h
    return out


def test_v33_lock_files_exist():
    assert LEAN.exists(), f"missing: {LEAN}"
    assert OUT.exists(), f"missing: {OUT} (run benchmark + tee first)"
    assert OUT.read_text(encoding="utf-8").strip(), "out file is empty (benchmark likely failed)"
    assert LOCK.exists(), f"missing: {LOCK} (run sha256sum lock step)"


def test_v33_locks_match():
    lock_map = parse_lock_lines(LOCK.read_text(encoding="utf-8"))

    lean_keys = [str(LEAN), str(LEAN.relative_to(ROOT)), LEAN.name]
    out_keys = [str(OUT), str(OUT.relative_to(ROOT)), OUT.name]

    exp_lean = next((lock_map.get(k) for k in lean_keys if lock_map.get(k)), None)
    exp_out = next((lock_map.get(k) for k in out_keys if lock_map.get(k)), None)

    assert exp_lean is not None and exp_out is not None, "lock file must include lean + out"

    assert sha256_file(LEAN) == exp_lean
    assert sha256_file(OUT) == exp_out