#!/usr/bin/env python3
"""Create or countersign exact-release GlyphChain/Legal evidence offline."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.aion_business.runtime.glyphchain_release_readiness import (
    EVIDENCE_SCHEMA,
    EVIDENCE_INVENTORY_SCHEMA,
    TASKS,
    sign_evidence,
)


MAX_ENTRY_BYTES = 1_000_000
MAX_ARTIFACT_BYTES = 250_000_000
MAX_KEY_BYTES = 64_000


def _regular_file(path: Path, *, label: str, maximum_bytes: int) -> bytes:
    value = path.expanduser()
    if value.is_symlink():
        raise SystemExit(f"Refusing symbolic-link {label}: {value}")
    if not value.is_file():
        raise SystemExit(f"{label} is not a regular file: {value}")
    size = value.stat().st_size
    if size > maximum_bytes:
        raise SystemExit(f"{label} exceeds {maximum_bytes} bytes: {value}")
    return value.read_bytes()


def _private_key(path: Path, *, password_environment: str | None) -> Ed25519PrivateKey:
    payload = _regular_file(path, label="signing key", maximum_bytes=MAX_KEY_BYTES)
    mode = path.expanduser().stat().st_mode & 0o777
    if mode & 0o077:
        raise SystemExit("Signing key file must be owner-only")
    password: bytes | None = None
    if password_environment:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", password_environment):
            raise SystemExit("Signing-key password environment name is invalid")
        password_value = os.getenv(password_environment)
        if password_value is None:
            raise SystemExit(f"Signing-key password environment is not set: {password_environment}")
        password = password_value.encode("utf-8")
    try:
        key = serialization.load_pem_private_key(payload, password=password)
    except (TypeError, ValueError) as exc:
        raise SystemExit("Signing key or supplied signing-key password is invalid") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("Release evidence signing key must be Ed25519")
    return key


def _artifact(value: str) -> dict[str, str]:
    try:
        kind, artifact_id, raw_path = value.split("=", 2)
    except ValueError as exc:
        raise SystemExit("Artifact must use KIND=ARTIFACT_ID=PATH") from exc
    kind = kind.strip()
    artifact_id = artifact_id.strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", kind):
        raise SystemExit(f"Artifact kind is invalid: {kind}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]*", artifact_id):
        raise SystemExit(f"Artifact identifier is invalid: {artifact_id}")
    path = Path(raw_path).expanduser()
    payload = _regular_file(path, label="evidence artifact", maximum_bytes=MAX_ARTIFACT_BYTES)
    return {"artifact_id": artifact_id, "kind": kind, "sha256": sha256(payload).hexdigest()}


def _validated_observed_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit("Evidence observation time must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise SystemExit("Evidence observation time must include a timezone")
    if parsed.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise SystemExit("Evidence observation time must not be in the future")
    return value


def _validate_body(task_id: str, body: dict[str, Any]) -> None:
    task = TASKS[task_id]
    if body.get("schema_version") != EVIDENCE_SCHEMA:
        raise SystemExit("Evidence body schema is unsupported")
    if str(body.get("task_id") or "").strip().upper() != task_id:
        raise SystemExit("Evidence task binding is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(body.get("release_manifest_sha256") or "").lower()):
        raise SystemExit("Evidence release-manifest digest is invalid")
    if body.get("environment") != "production" or body.get("result") != "PASS":
        raise SystemExit("Evidence must record a production PASS result")
    statement = str(body.get("statement") or "").strip()
    if not statement or len(statement) > 4096:
        raise SystemExit("Evidence statement must contain 1 to 4096 characters")
    _validated_observed_at(str(body.get("observed_at") or ""))
    artifacts = body.get("artifacts")
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 32:
        raise SystemExit("Evidence must contain 1 to 32 artifact commitments")
    identifiers: set[str] = set()
    kinds: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise SystemExit("Evidence artifact is invalid")
        artifact_id = str(artifact.get("artifact_id") or "").strip()
        kind = str(artifact.get("kind") or "").strip()
        digest = str(artifact.get("sha256") or "").lower()
        if (
            not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{0,159}", artifact_id)
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,119}", kind)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise SystemExit("Evidence artifact fields are invalid")
        if artifact_id in identifiers:
            raise SystemExit("Evidence artifact identifiers must be unique")
        identifiers.add(artifact_id)
        kinds.add(kind)
    missing = sorted(set(task["required_artifact_kinds"]) - kinds)
    if missing:
        raise SystemExit("Missing required artifact kinds: " + ", ".join(missing))


def _exclusive_json(path: Path, value: dict[str, Any]) -> None:
    output = path.expanduser()
    if output.is_symlink():
        raise SystemExit(f"Refusing symbolic-link evidence output: {output}")
    if output.suffix.lower() != ".json":
        raise SystemExit("Release evidence output must use .json")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise SystemExit(f"Refusing to replace existing evidence output: {output}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        output.unlink(missing_ok=True)
        raise


def _create(arguments: argparse.Namespace) -> dict[str, Any]:
    task_id = str(arguments.task_id).strip().upper()
    task = TASKS.get(task_id)
    if task is None:
        raise SystemExit(f"Unknown release task: {task_id}")
    release = _regular_file(
        arguments.release_manifest,
        label="release manifest",
        maximum_bytes=MAX_ARTIFACT_BYTES,
    )
    artifacts = [_artifact(value) for value in arguments.artifact]
    if len(artifacts) > 32:
        raise SystemExit("A release evidence entry accepts at most 32 artifacts")
    kinds = {artifact["kind"] for artifact in artifacts}
    missing = sorted(set(task["required_artifact_kinds"]) - kinds)
    if missing:
        raise SystemExit("Missing required artifact kinds: " + ", ".join(missing))
    if len({artifact["artifact_id"] for artifact in artifacts}) != len(artifacts):
        raise SystemExit("Artifact identifiers must be unique")
    observed_at = arguments.observed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _validated_observed_at(observed_at)
    signer_id = str(arguments.signer_id).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", signer_id):
        raise SystemExit("Signer identifier is invalid")
    body = {
        "schema_version": EVIDENCE_SCHEMA,
        "task_id": task_id,
        "release_manifest_sha256": sha256(release).hexdigest(),
        "environment": "production",
        "result": "PASS",
        "observed_at": observed_at,
        "statement": str(arguments.statement).strip(),
        "artifacts": artifacts,
    }
    if not body["statement"]:
        raise SystemExit("Evidence statement must not be empty")
    _validate_body(task_id, body)
    key = _private_key(
        arguments.private_key,
        password_environment=arguments.key_password_environment,
    )
    return {
        "task_id": task_id,
        "body": body,
        "attestations": [sign_evidence(body, signer_id=signer_id, private_key=key)],
    }


def _attest(arguments: argparse.Namespace) -> dict[str, Any]:
    payload = _regular_file(arguments.entry, label="evidence entry", maximum_bytes=MAX_ENTRY_BYTES)
    try:
        entry = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SystemExit("Evidence entry is not valid UTF-8 JSON") from exc
    if not isinstance(entry, dict) or not isinstance(entry.get("body"), dict):
        raise SystemExit("Evidence entry body is missing")
    task_id = str(entry.get("task_id") or "").strip().upper()
    if task_id not in TASKS or str(entry["body"].get("task_id") or "").strip().upper() != task_id:
        raise SystemExit("Evidence task binding is invalid")
    _validate_body(task_id, entry["body"])
    attestations = entry.get("attestations")
    if not isinstance(attestations, list):
        raise SystemExit("Evidence attestations array is missing")
    signer_id = str(arguments.signer_id).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", signer_id):
        raise SystemExit("Signer identifier is invalid")
    if any(isinstance(item, dict) and item.get("signer_id") == signer_id for item in attestations):
        raise SystemExit(f"Signer already attested this evidence entry: {signer_id}")
    key = _private_key(
        arguments.private_key,
        password_environment=arguments.key_password_environment,
    )
    return {
        "task_id": task_id,
        "body": entry["body"],
        "attestations": [
            *attestations,
            sign_evidence(entry["body"], signer_id=signer_id, private_key=key),
        ],
    }


def _inventory(arguments: argparse.Namespace) -> dict[str, Any]:
    if len(arguments.entry) > len(TASKS):
        raise SystemExit(f"Evidence inventory accepts at most {len(TASKS)} entries")
    entries: list[dict[str, Any]] = []
    task_ids: set[str] = set()
    release_digests: set[str] = set()
    for path in arguments.entry:
        payload = _regular_file(path, label="evidence entry", maximum_bytes=MAX_ENTRY_BYTES)
        try:
            entry = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SystemExit(f"Evidence entry is not valid UTF-8 JSON: {path}") from exc
        if not isinstance(entry, dict) or not isinstance(entry.get("body"), dict):
            raise SystemExit(f"Evidence entry body is missing: {path}")
        task_id = str(entry.get("task_id") or "").strip().upper()
        if task_id not in TASKS:
            raise SystemExit(f"Evidence entry has an unknown task: {task_id}")
        if task_id in task_ids:
            raise SystemExit(f"Evidence inventory contains duplicate task: {task_id}")
        _validate_body(task_id, entry["body"])
        attestations = entry.get("attestations")
        if not isinstance(attestations, list) or not attestations:
            raise SystemExit(f"Evidence entry has no attestations: {task_id}")
        task_ids.add(task_id)
        release_digests.add(str(entry["body"]["release_manifest_sha256"]).lower())
        entries.append(entry)
    if len(release_digests) != 1:
        raise SystemExit("Evidence inventory entries must bind one exact release manifest")
    entries.sort(key=lambda entry: str(entry["task_id"]))
    return {
        "schema_version": EVIDENCE_INVENTORY_SCHEMA,
        "release_manifest_sha256": next(iter(release_digests)),
        "evidence_entries": entries,
        "claim_boundary": (
            "This inventory assembles signed evidence for one exact release. "
            "Authority roles, signatures and release readiness remain subject to evaluator verification."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_subparsers(dest="mode", required=True)

    create = modes.add_parser("create", help="Hash artifacts and create the first signed evidence entry")
    create.add_argument("--task-id", required=True)
    create.add_argument("--release-manifest", type=Path, required=True)
    create.add_argument("--artifact", action="append", required=True, metavar="KIND=ARTIFACT_ID=PATH")
    create.add_argument("--statement", required=True)
    create.add_argument("--observed-at")
    create.add_argument("--signer-id", required=True)
    create.add_argument("--private-key", type=Path, required=True)
    create.add_argument("--key-password-environment")
    create.add_argument("--output", type=Path, required=True)

    attest = modes.add_parser("attest", help="Countersign the unchanged body with a separate authority key")
    attest.add_argument("--entry", type=Path, required=True)
    attest.add_argument("--signer-id", required=True)
    attest.add_argument("--private-key", type=Path, required=True)
    attest.add_argument("--key-password-environment")
    attest.add_argument("--output", type=Path, required=True)

    inventory = modes.add_parser("inventory", help="Build one deterministic exact-release evidence inventory")
    inventory.add_argument("--entry", type=Path, action="append", required=True)
    inventory.add_argument("--output", type=Path, required=True)

    arguments = parser.parse_args()
    if arguments.mode == "create":
        value = _create(arguments)
    elif arguments.mode == "attest":
        value = _attest(arguments)
    else:
        value = _inventory(arguments)
    _exclusive_json(arguments.output, value)
    summary = {"output": str(arguments.output.expanduser()), "mode": arguments.mode}
    if arguments.mode == "inventory":
        summary.update({
            "entry_count": len(value["evidence_entries"]),
            "release_manifest_sha256": value["release_manifest_sha256"],
        })
    else:
        summary.update({
            "task_id": value["task_id"],
            "attestation_count": len(value["attestations"]),
        })
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
