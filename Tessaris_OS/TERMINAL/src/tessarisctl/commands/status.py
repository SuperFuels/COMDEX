from __future__ import annotations
import os, subprocess, sys
from pathlib import Path

def _run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()

def add_parser(subparsers):
    p = subparsers.add_parser("status", help="Show repo + registry + artifacts status")
    p.add_argument("--no-registry", action="store_true", help="Skip registry verify")
    p.set_defaults(func=main)

def main(args) -> int:
    # git summary
    rc, out = _run(["git", "status", "-sb"])
    print(out if out else "(git status unavailable)")
    print()

    # show untracked artifacts count (if any)
    rc, out = _run(["git", "status", "--porcelain"])
    lines = out.splitlines() if out else []
    untracked_artifacts = [l for l in lines if l.startswith("?? ") and "/artifacts/" in l]
    if untracked_artifacts:
        print(f"UNTRACKED artifacts: {len(untracked_artifacts)} (consider .gitignore **/artifacts/**)")
    else:
        print("Artifacts: OK (no untracked artifacts showing)")
    print()

    if args.no_registry:
        return 0

    # registry verify (best-effort)
    env = os.environ.copy()
    # keep whatever PYTHONPATH user set; don't override
    rc, out = _run([sys.executable, "-m", "tessarisctl", "registry", "verify"])
    print(out)
    return 0 if rc == 0 else rc
