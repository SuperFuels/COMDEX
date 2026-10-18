#!/usr/bin/env python3
"""Run the bounded, content-free local GlyphChain network exercise."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.consensus.network_qualification import NetworkQualificationExercise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exercise-root", type=Path, required=True)
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--validator-checkpoint-id", required=True)
    parser.add_argument("--governance-approval-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    release_digest = sha256(args.release_manifest.read_bytes()).hexdigest()
    exercise = NetworkQualificationExercise(args.exercise_root)
    report = exercise.run(
        release_manifest_sha256=release_digest,
        validator_checkpoint_id=args.validator_checkpoint_id,
        governance_approval_id=args.governance_approval_id,
    )
    output = exercise.write_report(args.output, report)
    print(json.dumps({
        "output": str(output), "result": report["result"],
        "production_ready": report["production_ready"],
        "report_sha256": report["report_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
