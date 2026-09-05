#!/usr/bin/env python3
"""Build the deterministic core AION department/industry capability library."""

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
SPECS = ROOT / "capability_packs" / "core_library_specs.json"


def _identity(path: Path | None) -> tuple[DeviceIdentity, bool]:
    if path:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("publisher_key_must_be_ed25519")
        return DeviceIdentity(key), False
    return DeviceIdentity(Ed25519PrivateKey.generate()), True


def _components(spec: dict) -> dict[str, bytes]:
    prompt = (
        f"You are AION's bounded {spec['name']} operator. Use only admitted inputs and the "
        f"authorized Business Map projection to {spec['purpose']}. Separate evidence from "
        f"inference. {spec['forbidden_claim']} Prepare work for review by default. Never perform "
        "an external action without its declared capability, exact approval and verified receipt.\n"
    ).encode()
    procedure = {
        "schema_version": "aion.capability.procedure.v1", "purpose": spec["purpose"],
        "steps": [
            {"id": "admit", "operation": "aion.admit", "effect": "read_only"},
            *[{"id": f"read_{index}", "operation": tool, "effect": "read_only"} for index, tool in enumerate(spec["read_tools"], 1)],
            {"id": "draft", "operation": spec["draft_tool"], "effect": "reversible"},
            {"id": "approve", "operation": "approval.require_exact_scope_and_content", "effect": "human_gate"},
            {"id": "act", "operation": spec["external_action"], "effect": "external"},
            {"id": "verify", "operation": "receipt.verify", "effect": "read_only"}
        ],
        "default_mode": "prepare_for_review"
    }
    tools = {"schema_version": "aion.capability.tools.v1",
             "tools": spec["read_tools"] + [spec["draft_tool"], "receipt.verify"],
             "execution_actions": [spec["external_action"]], "bundles_credentials": False,
             "requires_authorized_adapter": True}
    policy = {"schema_version": "aion.capability.policy.v1", "department": spec["department"],
              "industry": spec["industry"], "default_mode": "prepare_for_review",
              "external_action_requires": ["exact_private_approval", "authorized_adapter", "provider_receipt"],
              "customer_content_may_not_enter_package_state": True,
              "model_may_not_write_canonical_memory": True, "forbidden_claim": spec["forbidden_claim"]}
    return {"prompt/v1.md": prompt,
            "procedure/v1.json": json.dumps(procedure, indent=2, sort_keys=True).encode(),
            "tools/v1.json": json.dumps(tools, indent=2, sort_keys=True).encode(),
            "policy/v1.json": json.dumps(policy, indent=2, sort_keys=True).encode()}


def build_library(output: Path, *, private_key_path: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    specs = json.loads(SPECS.read_text(encoding="utf-8"))
    identity, development = _identity(private_key_path)
    built = []
    for key, spec in sorted(specs.items()):
        package_id = f"aion.{spec['department']}.{key}"
        artifact = output / f"{package_id}-1.0.0.zip"
        components = _components(spec)
        with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative, raw in sorted(components.items()):
                info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0)); info.external_attr = 0o100644 << 16
                archive.writestr(info, raw)
        raw = artifact.read_bytes()
        tool_spec = json.loads(components["tools/v1.json"])
        payload = {
            "package_id": package_id, "version": "1.0.0", "name": spec["name"],
            "department": spec["department"], "industry": spec["industry"],
            "artifact": {"filename": artifact.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
            "permissions": {"network_hosts": [], "file_roots": [],
                            "identity_scopes": [f"business.{spec['department']}.read", f"business.{spec['department']}.draft"],
                            "tools": tool_spec["tools"], "execution_actions": tool_spec["execution_actions"]},
            "limits": {"maximum_authorizations": 10000, "maximum_seconds": 120, "maximum_cost": 2.0},
            "components": {name: "v1" for name in ("prompt", "procedure", "tools", "policy")},
            "component_versions": {name: ["v1"] for name in ("prompt", "procedure", "tools", "policy")},
            "publishing": {"publisher_class": "tessaris", "curated": True,
                           "commercial_terms": "free_or_entitled_department_operation"},
            "contains_customer_brain": False, "contains_customer_data": False,
            "requires_authorized_connector": True, "live_delivery_qualified": False,
            "development_publisher_identity": development
        }
        manifest = CapabilityPackageAuthority.sign_manifest(payload, identity)
        manifest_path = output / f"{package_id}-1.0.0.manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        built.append({"package_ref": f"{package_id}@1.0.0", "artifact": artifact, "manifest": manifest_path})
    index = {"schema_version": "aion.capability_pack_library.v1", "publisher_public_key": identity.public_key_b64,
             "development_publisher_identity": development,
             "packages": [{"package_ref": row["package_ref"], "artifact": row["artifact"].name,
                           "manifest": row["manifest"].name} for row in built]}
    (output / "library-index.json").write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return {"index": index, "packages": built}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT / "dist" / "capability-packs" / "core")
    parser.add_argument("--publisher-private-key", type=Path); args = parser.parse_args()
    result = build_library(args.output.resolve(), private_key_path=args.publisher_private_key)
    print(json.dumps({"index": str(args.output.resolve() / "library-index.json"), "packages": len(result["packages"])}, indent=2))


if __name__ == "__main__":
    main()
