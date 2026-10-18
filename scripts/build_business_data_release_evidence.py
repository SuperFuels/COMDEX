#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.modules.aion_business.runtime.business_data_discovery import load_manifest

from backend.modules.aion_business.runtime.business_data_release_evidence import (
    build_business_data_release_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build fail-closed business-data evidence for a signed Tessaris release."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--scenario-catalogue", type=Path, required=True)
    parser.add_argument("--audit-report", type=Path, required=True)
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    trace_paths = [
        args.trace_root / f"{item['id']}.json"
        for item in manifest["required_discovery_sessions"]
        if (args.trace_root / f"{item['id']}.json").is_file()
    ]
    evidence = build_business_data_release_evidence(
        manifest_path=args.manifest,
        scenario_catalogue_path=args.scenario_catalogue,
        audit_report_path=args.audit_report,
        trace_report_paths=trace_paths,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
