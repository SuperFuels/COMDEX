from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Tuple


REQUIRED = ("run.json", "metrics.csv", "meta.json", "config.json")


def iter_run_dirs(root: Path) -> Iterable[Path]:
    # find folders that contain run.json
    for p in root.rglob("run.json"):
        yield p.parent


def check_run_dir(run_dir: Path) -> Tuple[bool, str]:
    missing = [f for f in REQUIRED if not (run_dir / f).exists()]
    if missing:
        return False, f"missing {missing}"

    # sanity: run.json must include key fields
    try:
        run = json.loads((run_dir / "run.json").read_text())
    except Exception as e:
        return False, f"run.json unreadable: {e}"

    for k in ("test_id", "run_hash", "controller", "seed"):
        if k not in run:
            return False, f"run.json missing key '{k}'"

    # metrics.csv basic check
    try:
        head = (run_dir / "metrics.csv").read_text().splitlines()[0]
        if "," not in head:
            return False, "metrics.csv missing header row"
    except Exception as e:
        return False, f"metrics.csv unreadable: {e}"

    return True, "OK"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="Artifacts root (e.g. MATTER/artifacts or BRIDGE/artifacts)")
    args = ap.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"ERROR: path not found: {root}")
        return 2

    run_dirs = sorted(iter_run_dirs(root))
    if not run_dirs:
        print(f"ERROR: no run.json found under {root}")
        return 3

    bad = 0
    for d in run_dirs:
        ok, msg = check_run_dir(d)
        rel = d.relative_to(root) if d.is_relative_to(root) else d
        if ok:
            print(f"OK   {rel}")
        else:
            bad += 1
            print(f"FAIL {rel} :: {msg}")

    if bad:
        print(f"\nFAILED: {bad} run(s) violate contract")
        return 1

    print(f"\nPASSED: {len(run_dirs)} run(s) satisfy contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
