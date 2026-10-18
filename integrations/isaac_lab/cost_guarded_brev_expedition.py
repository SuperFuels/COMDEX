#!/usr/bin/env python3
"""Run one frozen Brev expedition with an unconditional stop guard."""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import time
from typing import Any


INSTANCE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
MAX_SPEND_USD = 10.0


def budget(rate_per_hour: float, maximum_minutes: int) -> dict[str, Any]:
    if not (0 < rate_per_hour <= 10):
        raise ValueError("invalid_hourly_rate")
    if not (1 <= maximum_minutes <= 240):
        raise ValueError("invalid_runtime_cap")
    estimated = rate_per_hour * maximum_minutes / 60.0
    if estimated > MAX_SPEND_USD:
        raise ValueError("estimated_spend_exceeds_guard")
    return {"rate_per_hour_usd": rate_per_hour, "maximum_minutes": maximum_minutes,
            "maximum_compute_spend_usd": round(estimated, 2)}


def status(name: str) -> str:
    payload = json.loads(subprocess.check_output(["brev", "ls", "--json"], text=True))
    for row in payload.get("workspaces", []):
        if row.get("name") == name:
            return str(row.get("status", "UNKNOWN"))
    return "MISSING"


def wait_ready(name: str, deadline: float) -> None:
    while time.monotonic() < deadline:
        if status(name) == "RUNNING":
            return
        time.sleep(5)
    raise TimeoutError("instance_readiness_timeout")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", default="aion-isaac-crusoe")
    parser.add_argument("--rate-per-hour", type=float, default=1.74)
    parser.add_argument("--maximum-minutes", type=int, default=45)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("runner_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not INSTANCE.fullmatch(args.instance):
        raise SystemExit("invalid_instance_name")
    guard = budget(args.rate_per_hour, args.maximum_minutes)
    print(json.dumps({"instance": args.instance, **guard, "auto_stop": True}, sort_keys=True))
    if args.dry_run:
        return 0
    if not args.runner_args or args.runner_args[0] != "--":
        raise SystemExit("runner arguments must follow --")

    deadline = time.monotonic() + args.maximum_minutes * 60
    remote = (
        "AION_ISAAC_WORKSPACE=/home/ubuntu/aion-isaaclab "
        "AION_ISAAC_CACHE=/home/ubuntu/aion-isaac-cache "
        "bash /home/ubuntu/aion-isaaclab/integrations/isaac_lab/run_brev_frozen_contract.sh "
        + " ".join(shlex.quote(value) for value in args.runner_args[1:])
    )
    try:
        subprocess.run(["brev", "start", args.instance], check=True)
        wait_ready(args.instance, deadline)
        remaining = max(1, int(deadline - time.monotonic()))
        completed = subprocess.run(["brev", "exec", args.instance, "--", remote],
                                   timeout=remaining, check=False)
        return completed.returncode
    finally:
        subprocess.run(["brev", "stop", args.instance], check=False)


if __name__ == "__main__":
    raise SystemExit(main())
