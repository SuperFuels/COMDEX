#!/usr/bin/env python3
"""Prepare the bounded journey-25 legacy fixture under an instrumented surface."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import tempfile

from backend.modules.aion_business.runtime.business_data_write_tracer import (
    BusinessDataWriteTracer,
)


SESSION_ID = "import-export-migration"
SCENARIO = "legacy-import-whole-business-export-and-readback"


def atomic_private_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--trace-root", required=True)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--application-root", required=True)
    parser.add_argument("--update-root", required=True)
    parser.add_argument("--vault-root", required=True)
    parser.add_argument("--secret-root", required=True)
    parser.add_argument("--fingerprint-key-base64", required=True)
    args = parser.parse_args()

    key = base64.b64decode(args.fingerprint_key_base64, validate=True)
    source = Path(args.source_root).resolve(strict=False)
    tracer = BusinessDataWriteTracer(
        source_root=Path(args.repository_root),
        application_root=Path(args.application_root),
        update_root=Path(args.update_root),
        vault_roots=[Path(args.vault_root)],
        secret_store_roots=[Path(args.secret_root)],
        excluded_roots=[Path(args.trace_root)],
        path_fingerprint_key=key,
    )
    with tracer:
        if source.exists() and any(source.rglob("*")):
            raise ValueError("legacy_qualification_source_must_be_empty")
        fixtures = {
            "business_map.json": {
                "schema_version": "tessaris.legacy-business-map.v1",
                "business_name": "Journey One Qualification Ltd",
                "operating_priority": "preserve customer-controlled continuity",
            },
            "departments_map.json": {
                "schema_version": "tessaris.legacy-departments-map.v1",
                "departments": [
                    {"id": "operations", "name": "Operations"},
                    {"id": "future-quality", "name": "Future Quality"},
                ],
            },
            "automations.json": {
                "schema_version": "tessaris.legacy-automations.v1",
                "automations": [
                    {"id": "weekly-continuity-review", "enabled": True, "owner": "founder"}
                ],
            },
        }
        for name, payload in fixtures.items():
            atomic_private_write(
                source / name,
                (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            )
        atomic_private_write(
            source / "originals" / "legacy-customer-handbook.txt",
            b"Journey 25 private customer handbook original.\n",
        )
    report = Path(args.trace_root) / f"{SESSION_ID}.filesystem_import.json"
    tracer.write_report(
        report,
        session_id=SESSION_ID,
        scenario=SCENARIO,
        scenario_completed=True,
        surface="filesystem_import",
    )
    result = tracer.report(
        session_id=SESSION_ID,
        scenario=SCENARIO,
        scenario_completed=True,
        surface="filesystem_import",
    )
    print(json.dumps({
        "ok": result["release_gate_passed"],
        "event_count": result["event_count"],
        "unsafe_write_count": result["unsafe_write_count"],
        "source_prepared": True,
        "customer_content_in_output": False,
    }, sort_keys=True))
    return 0 if result["release_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
