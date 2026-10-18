#!/usr/bin/env python3
"""Build a governance-signed release-evidence trust-root inventory."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.aion_business.runtime.glyphchain_release_readiness import (
    TASKS,
    TRUST_ROOTS_SCHEMA,
    sign_trust_root_inventory,
)
from backend.scripts.create_glyphchain_release_evidence import (
    _exclusive_json,
    _private_key,
    _regular_file,
)


def _signer_id(value: str) -> str:
    result = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", result):
        raise SystemExit(f"Signer identifier is invalid: {result}")
    return result


def _assignment(value: str, *, label: str) -> tuple[str, str]:
    try:
        signer_id, assigned = value.split("=", 1)
    except ValueError as exc:
        raise SystemExit(f"{label} must use SIGNER_ID=VALUE") from exc
    return _signer_id(signer_id), assigned.strip()


def _public_key(path: Path) -> Ed25519PublicKey:
    payload = _regular_file(path, label="evidence-signer public key", maximum_bytes=64_000)
    try:
        key = serialization.load_pem_public_key(payload)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Evidence-signer public key is not valid PEM: {path}") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise SystemExit(f"Evidence-signer public key must be Ed25519: {path}")
    return key


def _exclusive_bytes(path: Path, payload: bytes, *, mode: int) -> None:
    output = path.expanduser()
    if output.is_symlink():
        raise SystemExit(f"Refusing symbolic-link authority public-key output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    except FileExistsError as exc:
        raise SystemExit(f"Refusing to replace authority public-key output: {output}") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        output.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True, metavar="SIGNER_ID=PUBLIC_KEY_PEM")
    parser.add_argument("--role", action="append", required=True, metavar="SIGNER_ID=ROLE")
    parser.add_argument("--independent", action="append", default=[], metavar="SIGNER_ID")
    parser.add_argument("--authority-id", required=True)
    parser.add_argument("--governance-private-key", type=Path, required=True)
    parser.add_argument("--key-password-environment")
    parser.add_argument("--authority-public-key-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    allowed_roles = {role for task in TASKS.values() for role in task["required_roles"]}
    roots: dict[str, dict[str, Any]] = {}
    raw_public_keys: dict[str, bytes] = {}
    for raw_assignment in arguments.root:
        signer_id, key_path = _assignment(raw_assignment, label="Root")
        if signer_id in roots:
            raise SystemExit(f"Duplicate trust-root signer: {signer_id}")
        key = _public_key(Path(key_path))
        key_bytes = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if key_bytes in raw_public_keys.values():
            raise SystemExit("One evidence-signer public key cannot represent multiple authorities")
        raw_public_keys[signer_id] = key_bytes
        roots[signer_id] = {
            "public_key_base64": base64.b64encode(key_bytes).decode("ascii"),
            "roles": [],
            "independent": False,
        }

    for raw in arguments.role:
        signer_id, role = _assignment(raw, label="Role")
        if signer_id not in roots:
            raise SystemExit(f"Role references unknown signer: {signer_id}")
        if role not in allowed_roles:
            raise SystemExit(f"Unknown release authority role: {role}")
        if role in roots[signer_id]["roles"]:
            raise SystemExit(f"Duplicate role assignment for {signer_id}: {role}")
        roots[signer_id]["roles"].append(role)

    for signer_id, root in roots.items():
        if not root["roles"]:
            raise SystemExit(f"Trust-root signer has no approved roles: {signer_id}")
        root["roles"].sort()
    for raw_signer_id in arguments.independent:
        signer_id = _signer_id(raw_signer_id)
        if signer_id not in roots:
            raise SystemExit(f"Independent assignment references unknown signer: {signer_id}")
        roots[signer_id]["independent"] = True

    authority_id = _signer_id(arguments.authority_id)
    governance_key = _private_key(
        arguments.governance_private_key,
        password_environment=arguments.key_password_environment,
    )
    governance_raw = governance_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    if governance_raw in raw_public_keys.values():
        raise SystemExit("Governance trust-root key must not also be an evidence-signer key")

    body = {
        "schema_version": TRUST_ROOTS_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "trust_roots": {signer_id: roots[signer_id] for signer_id in sorted(roots)},
        "claim_boundary": (
            "This signed inventory authorizes evidence-verification keys and roles. "
            "Its governance public key must be obtained through an independent approved channel."
        ),
    }
    document = {
        **body,
        "attestation": sign_trust_root_inventory(
            body,
            authority_id=authority_id,
            private_key=governance_key,
        ),
    }
    public_pem = governance_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    for output in (arguments.output.expanduser(), arguments.authority_public_key_output.expanduser()):
        if output.is_symlink() or output.exists():
            raise SystemExit(f"Refusing to replace trust-root output: {output}")
    _exclusive_json(arguments.output, document)
    try:
        _exclusive_bytes(arguments.authority_public_key_output, public_pem, mode=0o644)
    except Exception:
        arguments.output.expanduser().unlink(missing_ok=True)
        raise
    inventory_sha256 = sha256(arguments.output.expanduser().read_bytes()).hexdigest()
    print(json.dumps({
        "output": str(arguments.output.expanduser()),
        "authority_public_key_output": str(arguments.authority_public_key_output.expanduser()),
        "authority_key_id": "ed25519:sha256:" + sha256(governance_raw).hexdigest(),
        "trust_root_inventory_sha256": inventory_sha256,
        "trust_root_count": len(roots),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
