# backend/tests/run_demo_photon.py
from __future__ import annotations
import sys
from pathlib import Path
import importlib

# repo root (…/COMDEX)
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Enable .photon imports
from backend.modules.photonlang.importer import install
install()

# Ensure the tests folder (where demo_math.photon lives) is importable
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

# Import the .photon module transparently
demo_math = importlib.import_module("demo_math")

out = demo_math.add_and_measure(2, 3)
assert isinstance(out, dict) and "z" in out and "m" in out, f"unexpected result: {out}"
print("OK", out)