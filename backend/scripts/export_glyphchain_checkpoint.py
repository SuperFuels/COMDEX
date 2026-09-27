#!/usr/bin/env python3
"""Export or independently verify a public GlyphChain validator checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.modules.consensus.finality_checkpoint import (
    load_trusted_checkpoint_from_env,
    verify_public_checkpoint,
    write_public_checkpoint,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", help="Write the configured public checkpoint to this file")
    action.add_argument("--verify", help="Verify this downloaded checkpoint file")
    parser.add_argument("--expected-id", help="Checkpoint ID obtained through a separate trusted channel")
    parser.add_argument("--expected-root", help="Validator-set root obtained through a separate trusted channel")
    args = parser.parse_args()

    if args.output:
        configured = load_trusted_checkpoint_from_env()
        if configured is None:
            parser.error("no trusted checkpoint is configured")
        path = write_public_checkpoint(configured.value, Path(args.output))
        print(json.dumps({
            "status": "EXPORTED",
            "path": str(path),
            "checkpoint_id": configured.checkpoint_id,
            "validator_set_root": configured.validator_set_root,
            "distribution_warning": "Publish the file and its expected ID through separate channels.",
        }, indent=2, sort_keys=True))
        return 0

    checkpoint = verify_public_checkpoint(
        args.verify,
        expected_checkpoint_id=args.expected_id,
        expected_validator_set_root=args.expected_root,
    )
    print(json.dumps({
        "status": "VERIFIED",
        "checkpoint_id": checkpoint["checkpoint_id"],
        "validator_set_root": checkpoint["validator_set_root"],
        "chain_id": checkpoint["chain_id"],
        "network_id": checkpoint["network_id"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
