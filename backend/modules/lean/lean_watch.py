# backend/modules/lean/lean_watch.py

import argparse
import os
import time
import subprocess
import shlex
from typing import Optional, List

POLL_SEC = 0.6

def _mtime(path: str) -> float:
    try:
        return os.stat(path).st_mtime
    except FileNotFoundError:
        return -1.0

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Watch a .lean file and auto-inject on change")
    ap.add_argument("--container", required=True, help="Target container json for injection")
    ap.add_argument("--lean", required=True, help="Source .lean to watch")
    ap.add_argument("--inject-args", default="--overwrite --auto-clean --dedupe --preview normalized --validate --summary",
                    help="Extra args passed to lean_inject_cli.py inject (default is sensible)")
    ap.add_argument("--pythonpath", default=".", help="PYTHONPATH value to use")
    args = ap.parse_args(argv)

    cmd = f'PYTHONPATH={shlex.quote(args.pythonpath)} python backend/modules/lean/lean_inject_cli.py inject ' \
          f'{shlex.quote(args.container)} {shlex.quote(args.lean)} {args.inject_args}'
    print(f"👀 Watching {args.lean}\nWill run:\n  {cmd}\n")

    last = _mtime(args.lean)
    if last < 0:
        print("File not found. Waiting for it to appear...")
    while True:
        cur = _mtime(args.lean)
        if cur > 0 and cur != last:
            last = cur
            print("\n— change detected —")
            try:
                subprocess.run(cmd, shell=True, check=False)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"[watch] error: {e}")
        time.sleep(POLL_SEC)

if __name__ == "__main__":
    raise SystemExit(main())