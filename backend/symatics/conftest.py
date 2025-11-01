# File: backend/symatics/tests/conftest.py
import sys
import os

# Add the COMDEX root to sys.path (go up 3 levels, not 4)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    print(f"[pytest:conftest] PYTHONPATH patched -> {ROOT}")