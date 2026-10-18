#!/usr/bin/env python3
"""Run the bounded local GlyphChain restart and multi-network soak."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.consensus.network_soak_qualification import NetworkSoakQualification


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exercise-root", type=Path, required=True)
    parser.add_argument("--networks", type=int, default=3)
    parser.add_argument("--cycles", type=int, default=256)
    parser.add_argument("--restart-interval", type=int, default=16)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    exercise = NetworkSoakQualification(arguments.exercise_root)
    report = exercise.run(
        network_count=arguments.networks,
        cycles_per_network=arguments.cycles,
        restart_interval=arguments.restart_interval,
    )
    output = exercise.write_report(arguments.output, report)
    print(json.dumps({
        "output": str(output), "result": report["result"],
        "production_ready": report["production_ready"],
        "report_sha256": report["report_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
