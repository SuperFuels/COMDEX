# backend/tests/conftest.py
from __future__ import annotations

import os
import pathlib
import tempfile
import pytest

# -------------------------------------------------------------------
# ChainSim test env MUST be set at import-time (before backend.main imports)
# -------------------------------------------------------------------

_TEST_DB_DIR = tempfile.mkdtemp(prefix="pytest_chain_sim_")
_TEST_DB_PATH = str(pathlib.Path(_TEST_DB_DIR) / "chain_sim.sqlite3")

# Force persistence on + force a single DB file for the entire pytest run.
# This avoids "ledger bound to a different DB than the test expects".
os.environ["CHAIN_SIM_PERSIST"] = "1"
os.environ["CHAIN_SIM_DB_PATH"] = _TEST_DB_PATH

# Keep tests deterministic unless a test explicitly overrides it
os.environ.setdefault("CHAIN_SIM_SIG_MODE", "off")


@pytest.fixture(scope="session")
def chain_sim_db_path() -> str:
    """Expose the chain_sim sqlite path used for this pytest run."""
    return _TEST_DB_PATH


# -------------------------------------------------------------------
# Theorem results dump (import lazily to avoid import-time side effects)
# -------------------------------------------------------------------

def pytest_sessionfinish(session, exitstatus):
    """At end of pytest run, dump theorem results to docs/rfc/theorems_results.md"""
    outdir = pathlib.Path("docs/rfc")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "theorems_results.md"

    # Import here (NOT at module import time) to avoid pulling heavy deps during collection
    try:
        from backend.tests import test_symatics_theorems as theorems  # type: ignore
        results = getattr(theorems, "THEOREM_RESULTS", [])
    except Exception:
        results = []

    with open(outfile, "w", encoding="utf-8") as f:
        f.write("# Symatics Theorems Results\n\n")
        f.write("Automated proof snapshot.\n\n")
        f.write("| Theorem | Statement | Result |\n")
        f.write("|---------|-----------|--------|\n")
        for name, stmt, status in results:
            icon = "✅" if status else "❌"
            f.write(f"| {name} | `{stmt}` | {icon} |\n")

    print(f"\n📄 Theorem results written to {outfile}\n")