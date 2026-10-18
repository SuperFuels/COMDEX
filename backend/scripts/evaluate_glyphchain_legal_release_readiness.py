#!/usr/bin/env python3
"""Evaluate exact-release evidence for all GlyphChain and Legal gates."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.aion_business.runtime.glyphchain_release_readiness import (
    EVIDENCE_INVENTORY_SCHEMA,
    TRUST_ROOTS_SCHEMA,
    GlyphChainReleaseReadinessError,
    GlyphChainReleaseReadinessEvaluator,
    verify_trust_root_inventory,
)


MAX_RELEASE_MANIFEST_BYTES = 250_000_000
MAX_EVIDENCE_INVENTORY_BYTES = 10_000_000
MAX_TRUST_ROOTS_BYTES = 2_000_000
MAX_PREAUTHORIZATION_REPORT_BYTES = 10_000_000


def _bytes(path: Path, *, label: str, maximum_bytes: int) -> bytes:
    value = path.expanduser()
    if value.is_symlink():
        raise SystemExit(f"Refusing symbolic-link {label}: {value}")
    if not value.is_file():
        raise SystemExit(f"{label} is not a regular file: {value}")
    if value.stat().st_size > maximum_bytes:
        raise SystemExit(f"{label} exceeds {maximum_bytes} bytes: {value}")
    return value.read_bytes()


def _object_payload(payload: bytes, *, label: str) -> dict:
    try:
        value = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SystemExit(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must contain a JSON object")
    return value


def _object(path: Path, *, label: str, maximum_bytes: int) -> dict:
    return _object_payload(
        _bytes(path, label=label, maximum_bytes=maximum_bytes),
        label=label,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--evidence-inventory", type=Path, required=True)
    parser.add_argument("--trust-roots", type=Path, required=True)
    parser.add_argument("--trust-roots-authority-public-key", type=Path)
    parser.add_argument("--expected-trust-roots-sha256")
    parser.add_argument("--preauthorization-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    release_manifest = _bytes(
        arguments.release_manifest,
        label="release manifest",
        maximum_bytes=MAX_RELEASE_MANIFEST_BYTES,
    )
    inventory = _object(
        arguments.evidence_inventory,
        label="release evidence inventory",
        maximum_bytes=MAX_EVIDENCE_INVENTORY_BYTES,
    )
    roots_payload = _bytes(
        arguments.trust_roots,
        label="release evidence trust roots",
        maximum_bytes=MAX_TRUST_ROOTS_BYTES,
    )
    roots = _object_payload(roots_payload, label="release evidence trust roots")
    if inventory.get("schema_version") != EVIDENCE_INVENTORY_SCHEMA:
        raise SystemExit("Release evidence inventory schema is unsupported")
    if roots.get("schema_version") != TRUST_ROOTS_SCHEMA:
        raise SystemExit("Release evidence trust-root schema is unsupported")
    if not isinstance(inventory.get("evidence_entries"), list):
        raise SystemExit("Release evidence inventory must contain an evidence_entries array")
    if not isinstance(roots.get("trust_roots"), dict):
        raise SystemExit("Release evidence trust-root inventory must contain a trust_roots object")
    trust_root_inventory_file_sha256 = sha256(roots_payload).hexdigest()
    authority_public_key: Ed25519PublicKey | None = None
    if roots["trust_roots"]:
        if arguments.trust_roots_authority_public_key is None:
            raise SystemExit("Non-empty trust roots require an independently supplied authority public key")
        expected_trust_roots_sha256 = str(arguments.expected_trust_roots_sha256 or "").lower()
        if expected_trust_roots_sha256 != trust_root_inventory_file_sha256:
            raise SystemExit("Trust-root inventory digest does not match the independently supplied pin")
        authority_payload = _bytes(
            arguments.trust_roots_authority_public_key,
            label="trust-root authority public key",
            maximum_bytes=64_000,
        )
        try:
            loaded_authority_public_key = serialization.load_pem_public_key(authority_payload)
        except (TypeError, ValueError) as exc:
            raise SystemExit("Trust-root authority public key is not valid PEM") from exc
        if not isinstance(loaded_authority_public_key, Ed25519PublicKey):
            raise SystemExit("Trust-root authority public key must be Ed25519")
        authority_public_key = loaded_authority_public_key
        if not verify_trust_root_inventory(roots, authority_public_key=authority_public_key):
            raise SystemExit("Trust-root inventory authority signature is invalid")
    release_digest = sha256(release_manifest).hexdigest()
    declared_release = str(inventory.get("release_manifest_sha256") or "").lower()
    if inventory["evidence_entries"] and declared_release != release_digest:
        raise SystemExit("Release evidence inventory does not bind the supplied release manifest")
    preauthorization_report_bytes: bytes | None = None
    if arguments.preauthorization_report is not None:
        preauthorization_report_bytes = _bytes(
            arguments.preauthorization_report,
            label="preauthorization readiness report",
            maximum_bytes=MAX_PREAUTHORIZATION_REPORT_BYTES,
        )
    evaluator = GlyphChainReleaseReadinessEvaluator()
    try:
        report = evaluator.evaluate(
            release_manifest_sha256=release_digest,
            evidence_entries=inventory.get("evidence_entries") or [],
            trust_root_inventory_bytes=roots_payload,
            trust_root_authority_public_key=authority_public_key,
            expected_trust_root_inventory_file_sha256=(
                arguments.expected_trust_roots_sha256 if roots["trust_roots"] else None
            ),
            preauthorization_report_bytes=preauthorization_report_bytes,
        )
    except GlyphChainReleaseReadinessError as exc:
        raise SystemExit(str(exc)) from exc
    output = evaluator.write_report(arguments.output, report)
    print(json.dumps({
        "output": str(output), "result": report["result"],
        "production_release_authorized": report["production_release_authorized"],
        "passed_count": report["passed_count"], "unmet_count": report["unmet_count"],
        "report_sha256": report["report_sha256"],
    }, sort_keys=True))
    return 0 if report["production_release_authorized"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
