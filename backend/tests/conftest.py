# backend/tests/conftest.py
import pathlib
from backend.tests import test_symatics_theorems as theorems

def pytest_sessionfinish(session, exitstatus):
    """At end of pytest run, dump theorem results to docs/rfc/theorems_results.md"""
    outdir = pathlib.Path("docs/rfc")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "theorems_results.md"

    with open(outfile, "w") as f:
        f.write("# Symatics Theorems Results\n\n")
        f.write("Automated proof snapshot.\n\n")
        f.write("| Theorem | Statement | Result |\n")
        f.write("|---------|-----------|--------|\n")
        for name, stmt, status in theorems.THEOREM_RESULTS:
            icon = "✅" if status else "❌"
            f.write(f"| {name} | `{stmt}` | {icon} |\n")

    print(f"\n📄 Theorem results written to {outfile}\n")