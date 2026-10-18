#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from backend.modules.aion_business.runtime.business_data_discovery import (
    DEFAULT_SOURCE_ROOTS,
    load_manifest,
    reconcile_scan,
    scan_repository,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit likely business-data persistence operations against the Tessaris vault manifest."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--source-root",
        action="append",
        dest="source_roots",
        help="Repository-relative source root to scan; repeat for multiple roots.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("config/business-data-manifest.v1.json"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="Write a deterministic aggregate baseline without source text or business values.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when unknown writes or incomplete discovery sessions remain.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    scan = scan_repository(root, source_roots=args.source_roots or DEFAULT_SOURCE_ROOTS)
    result = reconcile_scan(scan, load_manifest(manifest_path))
    report = {"scan": scan, "reconciliation": result}

    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.summary_output:
        summary_output = (
            args.summary_output if args.summary_output.is_absolute() else root / args.summary_output
        )
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        by_area = Counter(
            "/".join(item["path"].split("/")[:3]) for item in result["unknown_findings"]
        )
        by_file = Counter(item["path"] for item in result["unknown_findings"])
        summary = {
            "schema_version": "tessaris.business-data-discovery-baseline.v1",
            "privacy": scan["privacy"],
            "scanned_files": scan["scanned_files"],
            "finding_count": result["finding_count"],
            "declared_count": result["declared_count"],
            "declared_release_approved_count": result[
                "declared_release_approved_count"
            ],
            "declared_release_blocking_count": result[
                "declared_release_blocking_count"
            ],
            "unknown_count": result["unknown_count"],
            "blocking_touchpoint_count": result["blocking_touchpoint_count"],
            "blocking_touchpoint_ids": result["blocking_touchpoint_ids"],
            "incomplete_discovery_session_count": result[
                "incomplete_discovery_session_count"
            ],
            "vault_boundary_ready": result["vault_boundary_ready"],
            "unknown_by_operation": dict(
                sorted(Counter(item["operation"] for item in result["unknown_findings"]).items())
            ),
            "highest_volume_areas": [
                {"area": area, "finding_count": count}
                for area, count in sorted(by_area.items(), key=lambda item: (-item[1], item[0]))[:30]
            ],
            "highest_volume_files": [
                {"path": path, "finding_count": count}
                for path, count in sorted(by_file.items(), key=lambda item: (-item[1], item[0]))[:30]
            ],
        }
        summary_output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    counts = Counter(item["operation"] for item in scan["findings"])
    print(f"Scanned files: {scan['scanned_files']}")
    print(f"Likely persistence operations: {scan['finding_count']}")
    print(f"Declared: {result['declared_count']}")
    print(f"Declared but release-blocking: {result['declared_release_blocking_count']}")
    print(f"Unknown: {result['unknown_count']}")
    print(f"Blocking touchpoints: {result['blocking_touchpoint_count']}")
    print(f"Incomplete discovery sessions: {result['incomplete_discovery_session_count']}")
    for operation, count in sorted(counts.items()):
        print(f"  {operation}: {count}")

    if args.strict and not result["vault_boundary_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
