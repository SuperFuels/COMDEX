#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.modules.aion_business.runtime.business_data_discovery import (
    DEFAULT_SOURCE_ROOTS,
    load_manifest,
    scan_repository,
)
from backend.modules.aion_business.runtime.business_data_discovery_triage import (
    build_business_data_triage_queue,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic content-free review queue for unknown and declared-blocking persistence writes."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-root", action="append", dest="source_roots")
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("config/business-data-manifest.v1.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    output = args.output if args.output.is_absolute() else root / args.output
    scan = scan_repository(root, source_roots=args.source_roots or DEFAULT_SOURCE_ROOTS)
    queue = build_business_data_triage_queue(
        scan=scan,
        manifest=load_manifest(manifest_path),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    temporary.replace(output)
    print(f"Unknown findings queued: {queue['unknown_finding_count']}")
    print(f"Declared-blocking findings queued: {queue['declared_blocking_finding_count']}")
    print(f"Total findings queued: {queue['queued_finding_count']}")
    print(f"Release ready: {queue['release_ready']}")
    return 0 if queue["release_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
