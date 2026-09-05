#!/usr/bin/env python3
"""Build and sign a zero-content CycloneDX record for the production lock."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash
from backend.modules.aion_fabric.identity import IdentityStore


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements-production.lock"
OUTPUT = ROOT / "dist" / "release-evidence" / "aion-flow-production-sbom.cdx.json"
SIGNATURE = ROOT / "dist" / "release-evidence" / "aion-flow-production-sbom.signature.json"
PACKAGE = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)")


def main() -> None:
    if not LOCK.exists():
        raise SystemExit("requirements-production.lock is missing")
    lock_bytes = LOCK.read_bytes()
    components = []
    for line in LOCK.read_text(encoding="utf-8").splitlines():
        match = PACKAGE.match(line.strip())
        if not match:
            continue
        name, version = match.groups()
        components.append({
            "type": "library", "name": name, "version": version,
            "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{version}",
        })
    components.sort(key=lambda item: item["name"].lower())
    serial_seed = sha256(lock_bytes).hexdigest()
    document = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "serialNumber": f"urn:uuid:{serial_seed[:8]}-{serial_seed[8:12]}-{serial_seed[12:16]}-{serial_seed[16:20]}-{serial_seed[20:32]}",
        "metadata": {
            "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "component": {"type": "application", "name": "Tessaris AION Flow production runtime", "version": "1"},
            "properties": [
                {"name": "tessaris:requirements-lock-sha256", "value": serial_seed},
                {"name": "tessaris:contains-customer-content", "value": "false"},
                {"name": "tessaris:excluded-feature-environments", "value": "research,weasyprint,legacy-ecdsa"},
            ],
        },
        "components": components,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    identity = IdentityStore(ROOT / ".runtime" / "release-identity").load_or_create()
    evidence = {
        "schema_version": "tessaris.release-evidence.v1",
        "artifact": str(OUTPUT.relative_to(ROOT)), "artifact_hash": canonical_hash(document),
        "requirements_lock_sha256": serial_seed, "component_count": len(components),
        "signer_public_key": identity.public_key_b64,
    }
    evidence["signature"] = identity.sign(canonical_bytes(evidence))
    SIGNATURE.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **evidence}, sort_keys=True))


if __name__ == "__main__":
    main()
