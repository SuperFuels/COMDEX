#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import importlib
import json
import os
from pathlib import Path
import sys

from backend.modules.aion_business.runtime.business_data_discovery_campaign import (
    build_discovery_campaign_status,
    run_discovery_session,
)
from backend.modules.aion_business.runtime.business_data_trace_aggregation import (
    aggregate_discovery_session_fragments,
)


def _callable(value: str):
    module_name, separator, attribute = value.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError("callable must use module:function")
    target = getattr(importlib.import_module(module_name), attribute)
    if not callable(target):
        raise ValueError("target is not callable")
    return target


def _fingerprint_key() -> bytes:
    encoded = os.environ.get("TESSARIS_DISCOVERY_FINGERPRINT_KEY_B64", "")
    try:
        key = base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise ValueError("TESSARIS_DISCOVERY_FINGERPRINT_KEY_B64 is invalid") from exc
    if len(key) < 32:
        raise ValueError("TESSARIS_DISCOVERY_FINGERPRINT_KEY_B64 must decode to at least 32 bytes")
    return key


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run or inspect privacy-safe Tessaris business-data discovery sessions."
    )
    parser.add_argument("--manifest", type=Path, default=Path("config/business-data-manifest.v1.json"))
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument(
        "--catalogue",
        type=Path,
        default=Path("config/business-data-discovery-scenarios.v1.json"),
    )
    parser.add_argument("--status-output", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--run", metavar="SESSION_ID")
    mode.add_argument("--aggregate", metavar="SESSION_ID")
    parser.add_argument("--scenario")
    parser.add_argument("--callable")
    parser.add_argument(
        "--surface",
        choices=("desktop_backend", "filesystem_import", "update_runner"),
        default="desktop_backend",
    )
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--application-root", type=Path)
    parser.add_argument("--update-root", type=Path)
    parser.add_argument("--vault-root", type=Path, action="append", dest="vault_roots")
    parser.add_argument(
        "--secret-store-root", type=Path, action="append", dest="secret_store_roots",
        help="Approved key or secret-store root observed during this journey.",
    )
    args = parser.parse_args()

    if args.run:
        if not all((args.scenario, args.callable, args.application_root, args.update_root, args.vault_roots)):
            parser.error("--run requires --scenario, --callable, --application-root, --update-root and --vault-root")
        run_discovery_session(
            manifest_path=args.manifest,
            scenario_catalogue_path=args.catalogue,
            trace_root=args.trace_root,
            session_id=args.run,
            scenario=args.scenario,
            scenario_callable=_callable(args.callable),
            source_root=args.source_root,
            application_root=args.application_root,
            update_root=args.update_root,
            vault_roots=args.vault_roots,
            secret_store_roots=args.secret_store_roots,
            path_fingerprint_key=_fingerprint_key(),
            surface=args.surface,
        )

    if args.aggregate:
        aggregate_discovery_session_fragments(
            manifest_path=args.manifest,
            catalogue_path=args.catalogue,
            trace_root=args.trace_root,
            session_id=args.aggregate,
        )

    status = build_discovery_campaign_status(
        manifest_path=args.manifest, trace_root=args.trace_root
    )
    if args.status_output:
        args.status_output.parent.mkdir(parents=True, exist_ok=True)
        args.status_output.write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps({
        "required": status["required_session_count"],
        "passed": status["passed_session_count"],
        "failed": status["failed_session_count"],
        "missing": status["missing_session_count"],
        "campaign_ready": status["campaign_ready"],
    }, sort_keys=True))
    return 0 if status["campaign_ready"] else 2


if __name__ == "__main__":
    sys.exit(main())
