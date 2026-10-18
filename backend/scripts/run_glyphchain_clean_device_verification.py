#!/usr/bin/env python3
"""Verify a Legal evidence package against a separately pinned trust release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.aion_business.runtime.legal_clean_device_verification import (  # noqa: E402
    verify_clean_device_package,
    write_clean_device_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-package", type=Path, required=True)
    parser.add_argument("--trust-release", type=Path, required=True)
    parser.add_argument(
        "--expected-checkpoint-id", required=True,
        help="Checkpoint ID obtained through a different trusted channel.",
    )
    parser.add_argument("--expected-release-manifest-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify_clean_device_package(
        evidence_package=args.evidence_package,
        trust_release_directory=args.trust_release,
        expected_checkpoint_id=args.expected_checkpoint_id,
        expected_release_manifest_sha256=args.expected_release_manifest_sha256,
    )
    path = write_clean_device_report(args.output, report)
    print(json.dumps({
        "output": str(path),
        "result": report["result"],
        "report_sha256": report["report_sha256"],
    }, sort_keys=True))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
