# backend/modules/lean/lean_watch.py
from __future__ import annotations

import argparse
import os
import time
import subprocess
from typing import Optional, List, Dict, Any, Callable

POLL_SEC = 0.6


def _mtime(path: str) -> float:
    try:
        return os.stat(path).st_mtime
    except FileNotFoundError:
        return -1.0


def _run_inject(container: str, lean: str, inject_args: List[str], pythonpath: str) -> None:
    """
    Run lean_inject_cli.py with given arguments in a subprocess.
    Cross-platform safe (no shell=True).
    """
    cmd: List[str] = [
        "python",
        "backend/modules/lean/lean_inject_cli.py",
        "inject",
        container,
        lean,
        *inject_args,
    ]

    env: Dict[str, str] = os.environ.copy()
    env["PYTHONPATH"] = pythonpath

    try:
        subprocess.run(cmd, check=False, env=env)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"[lean_watch] inject error: {e}")


def watch_lean_session(
    lean_path: str,
    *,
    container_path: Optional[str] = None,
    inject_args: Optional[List[str]] = None,
    pythonpath: str = ".",
    mode: str = "integrated",
    normalize: bool = False,
    no_initial: bool = False,
    poll_sec: float = POLL_SEC,
    callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> bool:
    """
    Watch a .lean file and auto-inject on change (API entrypoint).

    If container_path is None, this becomes a pure watcher (events only).
    callback(event) gets:
      { event: "start"|"missing"|"initial"|"change"|"inject"|"error",
        lean: <path>, container: <path|None>, mtime: <float>, detail?: <str> }
    """
    def emit(evt: Dict[str, Any]) -> None:
        if callback:
            try:
                callback(evt)
            except Exception:
                pass

    inject_args = inject_args or []
    base_args = list(inject_args) + ["--mode", mode]
    if normalize:
        base_args.append("--normalize")

    emit({"event": "start", "lean": lean_path, "container": container_path, "mtime": _mtime(lean_path)})

    last = _mtime(lean_path)
    if last < 0:
        print("⚠️ File not found. Waiting for it to appear...")
        emit({"event": "missing", "lean": lean_path, "container": container_path, "mtime": last})

    # initial run
    if not no_initial and last > 0 and container_path:
        print("▶️ Initial run...")
        emit({"event": "initial", "lean": lean_path, "container": container_path, "mtime": last})
        _run_inject(container_path, lean_path, base_args, pythonpath)
        emit({"event": "inject", "lean": lean_path, "container": container_path, "mtime": last})

    try:
        while True:
            cur = _mtime(lean_path)
            if cur > 0 and cur != last:
                last = cur
                print("\n- change detected -")
                emit({"event": "change", "lean": lean_path, "container": container_path, "mtime": last})

                if container_path:
                    _run_inject(container_path, lean_path, base_args, pythonpath)
                    emit({"event": "inject", "lean": lean_path, "container": container_path, "mtime": last})

            time.sleep(poll_sec)
    except KeyboardInterrupt:
        return True
    except Exception as e:
        emit({"event": "error", "lean": lean_path, "container": container_path, "mtime": last, "detail": str(e)})
        return False


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Watch a .lean file and auto-inject on change")
    ap.add_argument("--container", required=True, help="Target container json for injection")
    ap.add_argument("--lean", required=True, help="Source .lean to watch")
    ap.add_argument("--mode", choices=["standalone", "integrated"], default="integrated")
    ap.add_argument("--normalize", action="store_true")
    ap.add_argument(
        "--inject-args",
        default="--overwrite --auto-clean --dedupe --preview normalized --validate --summary",
        help="Extra args passed to lean_inject_cli.py inject (in addition to mode/normalize)",
    )
    ap.add_argument("--pythonpath", default=".")
    ap.add_argument("--no-initial", action="store_true")
    ap.add_argument("--poll-sec", type=float, default=POLL_SEC)
    args = ap.parse_args(argv)

    print(f"👀 Watching {args.lean}")
    print(f"Target container: {args.container}")
    print(f"Mode: {args.mode}, Normalize: {args.normalize}")
    print(f"Inject args: {args.inject_args}")
    print()

    inject_args = args.inject_args.split() if args.inject_args else []
    ok = watch_lean_session(
        args.lean,
        container_path=args.container,
        inject_args=inject_args,
        pythonpath=args.pythonpath,
        mode=args.mode,
        normalize=args.normalize,
        no_initial=args.no_initial,
        poll_sec=args.poll_sec,
        callback=None,
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())