import hashlib
from pathlib import Path

RFC_DIR = Path("docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/v39_bridge")
LEAN_RFC = RFC_DIR / "V39_RangePrefixIndexNoMaterialization.lean"
OUT_RFC = RFC_DIR / "v39_range_prefix_index_no_materialization_out.txt"

LOCK_BACKEND = Path("backend/tests/locks/v39_range_prefix_index_no_materialization_lock.sha256")

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_lock(p: Path) -> dict:
    m = {}
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        assert len(parts) == 2, f"bad lock line: {line!r}"
        m[parts[1]] = parts[0]
    return m

def test_v39_lock_has_expected_entries():
    assert LOCK_BACKEND.exists(), "lock file missing"
    lock = parse_lock(LOCK_BACKEND)
    assert "V39_RangePrefixIndexNoMaterialization.lean" in lock, "lock file must include lean"
    assert "v39_range_prefix_index_no_materialization_out.txt" in lock, "lock file must include out"

def test_v39_lock_matches_rfc_artifacts():
    assert LEAN_RFC.exists(), f"missing RFC lean: {LEAN_RFC}"
    assert OUT_RFC.exists(), f"missing RFC out: {OUT_RFC}"
    lock = parse_lock(LOCK_BACKEND)

    exp_lean = sha256_file(LEAN_RFC)
    exp_out = sha256_file(OUT_RFC)

    assert lock["V39_RangePrefixIndexNoMaterialization.lean"] == exp_lean
    assert lock["v39_range_prefix_index_no_materialization_out.txt"] == exp_out

    # sanity: ensure drift anchor exists in output
    out_txt = OUT_RFC.read_text()
    assert "drift_sha256=" in out_txt
