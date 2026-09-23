#!/usr/bin/env python3
"""Build a deterministic, signed Sales/Lead Response capability package."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.capability_packages import CapabilityPackageAuthority
from backend.modules.aion_fabric.identity import DeviceIdentity


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "capability_packs" / "sales_lead_response"
FILES = ("prompt/v1.md", "procedure/v1.json", "tools/v1.json", "policy/v1.json")


def _identity(private_key_path: Path | None) -> tuple[DeviceIdentity, bool]:
    if private_key_path:
        raw = private_key_path.read_bytes()
        key = serialization.load_pem_private_key(raw, password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("publisher_key_must_be_ed25519")
        return DeviceIdentity(key), False
    return DeviceIdentity(Ed25519PrivateKey.generate()), True


def build(output: Path, *, private_key_path: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / "aion-sales-lead-response-1.0.0.zip"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in FILES:
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (SOURCE / relative).read_bytes())
    raw = artifact.read_bytes()
    identity, development_identity = _identity(private_key_path)
    payload = {
        "package_id": "aion.sales.lead_response",
        "version": "1.0.0",
        "name": "Sales and Lead Response",
        "department": "sales",
        "industry": "general",
        "artifact": {"filename": artifact.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
        "permissions": {
            "network_hosts": [],
            "file_roots": [],
            "identity_scopes": ["business.sales.read", "business.contacts.resolve", "business.sales.draft"],
            "tools": ["business_map.read", "inbound_lead.read", "contact.resolve", "email.prepare_draft", "email.send", "receipt.verify"],
            "execution_actions": ["email.send_approved", "crm.record_verified"]
        },
        "limits": {"maximum_authorizations": 10000, "maximum_seconds": 120, "maximum_cost": 2.0},
        "components": {"prompt": "v1", "procedure": "v1", "tools": "v1", "policy": "v1"},
        "component_versions": {"prompt": ["v1"], "procedure": ["v1"], "tools": ["v1"], "policy": ["v1"]},
        "publishing": {"publisher_class": "tessaris", "curated": True, "commercial_terms": "free_or_entitled_department_operation"},
        "contains_customer_brain": False,
        "contains_customer_data": False,
        "requires_authorized_connector": True,
        "live_delivery_qualified": False,
        "development_publisher_identity": development_identity
    }
    manifest = CapabilityPackageAuthority.sign_manifest(payload, identity)
    manifest_path = output / "aion-sales-lead-response-1.0.0.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {"artifact": artifact, "manifest": manifest_path, "publisher_public_key": identity.public_key_b64}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "capability-packs")
    parser.add_argument("--publisher-private-key", type=Path)
    args = parser.parse_args()
    built = build(args.output.resolve(), private_key_path=args.publisher_private_key)
    print(json.dumps({key: str(value) for key, value in built.items()}, indent=2))


if __name__ == "__main__":
    main()
