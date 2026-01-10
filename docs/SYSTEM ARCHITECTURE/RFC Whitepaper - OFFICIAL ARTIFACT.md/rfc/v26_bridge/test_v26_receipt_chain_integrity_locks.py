import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]  # /workspaces/COMDEX
LOCKDIR = ROOT / "backend" / "tests" / "locks"

SCRIPT = ROOT / "backend" / "tests" / "glyphos_wirepack_v26_receipt_chain_integrity_benchmark.py"
OUT = LOCKDIR / "v26_receipt_chain_integrity_out.txt"
LOCK = LOCKDIR / "v26_receipt_chain_integrity_lock.sha256"


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
        h, p = parts[0], parts[1]
        out[p] = h
        out[Path(p).name] = h   # <-- add this
    return out


def test_v26_lock_files_exist():
    assert SCRIPT.exists(), f"missing: {SCRIPT}"
    assert OUT.exists(), f"missing: {OUT} (run benchmark + tee first)"
    assert LOCK.exists(), f"missing: {LOCK} (run sha256sum lock step)"


def test_v26_locks_match():
    lock_map = parse_lock_lines(LOCK.read_text(encoding="utf-8"))
    # We lock by basename to be robust across paths.
    exp_script = lock_map.get(str(SCRIPT), lock_map.get(SCRIPT.name))
    exp_out = lock_map.get(str(OUT), lock_map.get(OUT.name))
    assert exp_script is not None and exp_out is not None, "lock file must include script + out"

    got_script = sha256_file(SCRIPT)
    got_out = sha256_file(OUT)

    assert got_script == exp_script
    assert got_out == exp_out