#!/usr/bin/env python3
"""Independently read journey 25's customer export and complete its surface proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.modules.aion_business.runtime.business_vault_portable_transfer import (
    BusinessVaultPortableExportService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", required=True)
    parser.add_argument("--passphrase", required=True)
    parser.add_argument("--fragment", required=True)
    args = parser.parse_args()

    payload = BusinessVaultPortableExportService.readback(
        export_path=args.export, passphrase=args.passphrase
    )
    summary = BusinessVaultPortableExportService.summary(payload)
    manifest = summary["manifest"]
    if not all(
        manifest.get(key) is True
        for key in (
            "includes_maps", "includes_departments", "includes_automations", "includes_originals"
        )
    ):
        raise ValueError("customer_export_required_coverage_missing")
    fragment_path = Path(args.fragment).resolve(strict=True)
    fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
    if (
        fragment.get("session_id") != "import-export-migration"
        or fragment.get("surface") != "filesystem_import"
        or fragment.get("release_gate_passed") is not True
    ):
        raise ValueError("customer_export_fragment_invalid")
    fragment["observed_external_classes"] = ["customer_export"]
    temporary = fragment_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(fragment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.chmod(0o600)
    temporary.replace(fragment_path)
    print(json.dumps({
        "ok": True,
        "record_count": manifest["record_count"],
        "original_count": manifest["original_count"],
        "required_coverage_complete": True,
        "customer_content_in_output": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
