from pathlib import Path

def test_locks_dir_exists():
    p = Path(__file__).resolve().parents[2] / "backend/tests/locks"
    assert p.exists() and p.is_dir(), f"Missing locks dir: {p}"