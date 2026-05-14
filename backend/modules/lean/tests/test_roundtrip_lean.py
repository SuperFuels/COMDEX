"""
Lean ↔ Glyph Roundtrip Regression Test
────────────────────────────────────────────
Ensures lean_to_glyph.py and glyph_to_lean.py preserve all declarations.
"""

import subprocess
import json
import difflib
from pathlib import Path

LEAN_FILE = Path("backend/modules/lean/examples/test_theorems.lean")
TMP_GLYPH = Path("backend/modules/lean/tests/tmp_roundtrip.glyph")
ROUNDTRIP = Path("roundtrip.lean")

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def test_roundtrip():
    # 1. Convert Lean -> Glyph
    run(f"python backend/modules/lean/lean_to_glyph.py {LEAN_FILE} > {TMP_GLYPH}")

    # 2. Convert Glyph -> Lean
    run(f"python -m backend.modules.lean.glyph_to_lean {TMP_GLYPH} --out {ROUNDTRIP}")

    # 3. Compare results
    with open(LEAN_FILE, "r") as f1, open(ROUNDTRIP, "r") as f2:
        orig, roundtrip = f1.read().split(), f2.read().split()

    diff = list(difflib.unified_diff(orig, roundtrip, lineterm=""))
    if diff:
        print("\n".join(diff))
        raise AssertionError("❌ Roundtrip mismatch detected.")
    else:
        print("✅ Roundtrip test passed - Lean -> Glyph -> Lean consistency verified.")

if __name__ == "__main__":
    test_roundtrip()