#!/usr/bin/env python3
"""Build or independently verify an immutable GlyphChain public trust release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.consensus.trust_release import (  # noqa: E402
    build_trust_release,
    verify_trust_release,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--verify", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument(
        "--verifier", type=Path,
        default=ROOT / "backend/modules/aion_business/static/tessaris-proof-verifier.html",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--release-version")
    parser.add_argument("--release-manifest-sha256")
    parser.add_argument("--expected-checkpoint-id")
    parser.add_argument("--expected-release-manifest-sha256")
    args = parser.parse_args()

    if args.build:
        required = {
            "--checkpoint": args.checkpoint,
            "--output": args.output,
            "--release-version": args.release_version,
            "--release-manifest-sha256": args.release_manifest_sha256,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            parser.error("required for --build: " + ", ".join(missing))
        result = build_trust_release(
            checkpoint_path=args.checkpoint,
            verifier_path=args.verifier,
            output_directory=args.output,
            release_version=args.release_version,
            release_manifest_sha256=args.release_manifest_sha256,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if not args.expected_checkpoint_id:
        parser.error("--expected-checkpoint-id from an independent channel is required for --verify")
    result = verify_trust_release(
        args.verify,
        expected_checkpoint_id=args.expected_checkpoint_id,
        expected_release_manifest_sha256=args.expected_release_manifest_sha256,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
