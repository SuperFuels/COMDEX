# File: backend/modules/lean/lean_watch.py

import argparse
import os
import time
import subprocess
from typing import Optional, List, Dict

POLL_SEC = 0.6


def _mtime(path: str) -> float:
    try:
        return os.stat(path).st_mtime
    except FileNotFoundError:
        return -1.0


def _run_inject(container: str, lean: str, inject_args: str, pythonpath: str) -> None:
    """
    Run lean_inject_cli.py with given arguments in a subprocess.
    Cross-platform safe (no shell command building).
    """
    cmd: List[str] = [
        "python", "backend/modules/lean/lean_inject_cli.py",
        "inject", container, lean
    ] + inject_args.split()

    env: Dict[str, str] = os.environ.copy()
    env["PYTHONPATH"] = pythonpath

    try:
        subprocess.run(cmd, check=False, env=env)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"[watch] error: {e}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Watch a .lean file and auto-inject on change")
    ap.add_argument("--container", required=True, help="Target container json for injection")
    ap.add_argument("--lean", required=True, help="Source .lean to watch")
    ap.add_argument(
        "--inject-args",
        default="--overwrite --auto-clean --dedupe --preview normalized --validate --summary",
        help="Extra args passed to lean_inject_cli.py inject"
    )
    ap.add_argument("--pythonpath", default=".", help="PYTHONPATH value to use")
    ap.add_argument("--no-initial", action="store_true", help="Skip initial inject run")
    args = ap.parse_args(argv)

    print(f"👀 Watching {args.lean}")
    print(f"Target container: {args.container}")
    print(f"Inject args: {args.inject_args}")
    print()

    last = _mtime(args.lean)
    if last < 0:
        print("⚠️ File not found. Waiting for it to appear...")

    # Initial run unless skipped
    if not args.no_initial and last > 0:
        print("▶️ Initial run...")
        _run_inject(args.container, args.lean, args.inject_args, args.pythonpath)

    while True:
        cur = _mtime(args.lean)
        if cur > 0 and cur != last:
            last = cur
            print("\n— change detected —")
            _run_inject(args.container, args.lean, args.inject_args, args.pythonpath)
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    raise SystemExit(main())