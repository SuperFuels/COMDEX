from __future__ import annotations
import os, platform, shutil, subprocess, sys
from pathlib import Path

def _ok(msg: str): print(f"[OK] {msg}")
def _warn(msg: str): print(f"[WARN] {msg}")
def _fail(msg: str): print(f"[FAIL] {msg}")

def add_parser(subparsers):
    p = subparsers.add_parser("doctor", help="Diagnostics for environment + repo health")
    p.add_argument("--full", action="store_true", help="Also run registry verify")
    p.set_defaults(func=main)

def main(args) -> int:
    # python
    pyver = sys.version.split()[0]
    _ok(f"Python: {pyver} ({sys.executable})")

    # repo root sanity
    root = Path.cwd()
    if not (root / ".git").exists():
        _warn("Not at repo root (no .git here). cd to /workspaces/COMDEX")
    else:
        _ok("Repo root: .git present")

    # tools
    for tool in ["git"]:
        if shutil.which(tool):
            _ok(f"{tool}: found")
        else:
            _fail(f"{tool}: missing in PATH")

    # PYTHONPATH sanity
    pp = os.environ.get("PYTHONPATH", "")
    if "Tessaris_OS/TERMINAL/src" in pp:
        _ok("PYTHONPATH includes Tessaris terminal src")
    else:
        _warn("PYTHONPATH does not include Tessaris terminal src (recommended)")
        print("      export PYTHONPATH=$PWD/Tessaris_OS/TERMINAL/src")

    # pytest availability
    try:
        import pytest  # noqa: F401
        _ok("pytest: import ok")
    except Exception as e:
        _fail(f"pytest: import failed: {e}")

    # trailing-space filenames check (common footgun)
    bad = []
    for p in root.rglob("* "):
        bad.append(str(p))
        if len(bad) >= 10:
            break
    if bad:
        _warn("Found filenames ending with a space (first 10):")
        for b in bad:
            print("      ", b)
    else:
        _ok("No trailing-space filenames detected")

    if not args.full:
        return 0

    # registry verify
    p = subprocess.run([sys.executable, "-m", "tessarisctl", "registry", "verify"])
    return p.returncode
