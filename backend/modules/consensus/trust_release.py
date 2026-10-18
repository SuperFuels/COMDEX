"""Immutable public trust-release packages for GlyphChain verification.

The checkpoint package and its expected checkpoint ID must be published through
different operational channels.  The package necessarily identifies its own
claimed checkpoint ID, but cannot make that value trusted; the verifier requires
the expected ID to be supplied independently.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from backend.modules.consensus.finality_checkpoint import (
    FinalityCheckpointError,
    normalize_checkpoint,
    verify_public_checkpoint,
)


class TrustReleaseError(ValueError):
    pass


SCHEMA_VERSION = "glyphchain.public-trust-release.v1"
CHECKPOINT_FILENAME = "validator-set.glyphchain-checkpoint"
VERIFIER_FILENAME = "tessaris-proof-verifier.html"
MANIFEST_FILENAME = "TRUST_RELEASE.json"
EXPECTED_FILES = {CHECKPOINT_FILENAME, VERIFIER_FILENAME, MANIFEST_FILENAME}
MAX_CHECKPOINT_BYTES = 1_000_000
MAX_VERIFIER_BYTES = 2_000_000
MAX_MANIFEST_BYTES = 256_000


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def _safe_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = Path(os.path.abspath(path))
    for component in (path, *path.parents):
        if component.is_symlink():
            raise TrustReleaseError("trust_release_symlink_refused")
    return path


def _read_bounded(path: Path, maximum: int, label: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise TrustReleaseError(f"trust_release_{label}_file_required")
    if path.stat().st_size > maximum:
        raise TrustReleaseError(f"trust_release_{label}_too_large")
    return path.read_bytes()


def _release_version(value: str) -> str:
    clean = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", clean):
        raise TrustReleaseError("trust_release_version_invalid")
    return clean


def _sha256_value(value: str, label: str) -> str:
    clean = str(value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", clean):
        raise TrustReleaseError(f"trust_release_{label}_invalid")
    return clean


def build_trust_release(
    *,
    checkpoint_path: str | Path,
    verifier_path: str | Path,
    output_directory: str | Path,
    release_version: str,
    release_manifest_sha256: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create one immutable public release directory without its trust pin."""

    checkpoint_source = _safe_path(checkpoint_path)
    verifier_source = _safe_path(verifier_path)
    output = _safe_path(output_directory)
    version = _release_version(release_version)
    release_digest = _sha256_value(release_manifest_sha256, "manifest_sha256")
    if output.exists():
        raise TrustReleaseError("trust_release_output_already_exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    os.mkdir(output, 0o755)

    try:
        checkpoint_bytes = _read_bounded(checkpoint_source, MAX_CHECKPOINT_BYTES, "checkpoint")
        verifier_bytes = _read_bounded(verifier_source, MAX_VERIFIER_BYTES, "verifier")
        try:
            checkpoint = normalize_checkpoint(json.loads(checkpoint_bytes))
        except (json.JSONDecodeError, UnicodeDecodeError, FinalityCheckpointError) as exc:
            raise TrustReleaseError("trust_release_checkpoint_invalid") from exc
        checkpoint_payload = (
            json.dumps(checkpoint, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        if b"fetch(" in verifier_bytes or b"http://" in verifier_bytes or b"https://" in verifier_bytes:
            raise TrustReleaseError("trust_release_verifier_is_not_offline_only")
        if b"checkpoint-pin" not in verifier_bytes or b"pin!==cpId" not in verifier_bytes:
            raise TrustReleaseError("trust_release_verifier_independent_pin_gate_missing")

        files = {
            CHECKPOINT_FILENAME: checkpoint_payload,
            VERIFIER_FILENAME: verifier_bytes,
        }
        for filename, payload in files.items():
            path = output / filename
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())

        manifest: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "release_version": version,
            "created_at": created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "release_manifest_sha256": release_digest,
            "checkpoint": {
                "checkpoint_id": checkpoint["checkpoint_id"],
                "validator_set_root": checkpoint["validator_set_root"],
                "chain_id": checkpoint["chain_id"],
                "network_id": checkpoint["network_id"],
                "epoch": checkpoint["epoch"],
                "effective_height": checkpoint["effective_height"],
            },
            "files": {
                filename: {"sha256": _digest(payload), "size_bytes": len(payload)}
                for filename, payload in sorted(files.items())
            },
            "privacy": "public cryptographic material only; no Legal document or private key",
            "distribution_boundary": (
                "The checkpoint's claimed ID is informational only. The expected "
                "checkpoint ID must be published and obtained through an independent "
                "trusted channel before this package can establish trust."
            ),
        }
        manifest["manifest_sha256"] = _digest(_canonical(manifest))
        manifest_payload = (
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        descriptor = os.open(
            output / MANIFEST_FILENAME,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(manifest_payload)
            handle.flush()
            os.fsync(handle.fileno())
        return {
            "status": "BUILT_NOT_PUBLISHED",
            "directory": str(output),
            "manifest": manifest,
            "independent_pin_candidate": checkpoint["checkpoint_id"],
            "pin_is_independently_published": False,
        }
    except Exception:
        # A partial directory is intentionally retained as evidence of an
        # interrupted build and can never be mistaken for a complete release
        # because TRUST_RELEASE.json is written last.
        raise


def verify_trust_release(
    directory: str | Path,
    *,
    expected_checkpoint_id: str,
    expected_release_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Verify the public package using a pin supplied outside the package."""

    root = _safe_path(directory)
    if not root.is_dir():
        raise TrustReleaseError("trust_release_directory_required")
    names = {item.name for item in root.iterdir()}
    if names != EXPECTED_FILES:
        raise TrustReleaseError("trust_release_file_set_invalid")
    for item in root.iterdir():
        if item.is_symlink() or not item.is_file():
            raise TrustReleaseError("trust_release_file_set_invalid")

    manifest_bytes = _read_bounded(root / MANIFEST_FILENAME, MAX_MANIFEST_BYTES, "manifest")
    try:
        manifest = json.loads(manifest_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TrustReleaseError("trust_release_manifest_invalid") from exc
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise TrustReleaseError("trust_release_manifest_invalid")
    supplied_manifest_digest = str(manifest.get("manifest_sha256") or "")
    unsigned_manifest = dict(manifest)
    unsigned_manifest.pop("manifest_sha256", None)
    if not hmac.compare_digest(supplied_manifest_digest, _digest(_canonical(unsigned_manifest))):
        raise TrustReleaseError("trust_release_manifest_digest_invalid")
    _release_version(str(manifest.get("release_version") or ""))
    release_digest = _sha256_value(
        str(manifest.get("release_manifest_sha256") or ""), "manifest_sha256",
    )
    if expected_release_manifest_sha256 and not hmac.compare_digest(
        release_digest,
        _sha256_value(expected_release_manifest_sha256, "expected_manifest_sha256"),
    ):
        raise TrustReleaseError("trust_release_source_manifest_mismatch")

    for filename, maximum in (
        (CHECKPOINT_FILENAME, MAX_CHECKPOINT_BYTES),
        (VERIFIER_FILENAME, MAX_VERIFIER_BYTES),
    ):
        payload = _read_bounded(root / filename, maximum, filename.split(".")[0])
        expected = dict((manifest.get("files") or {}).get(filename) or {})
        if expected.get("size_bytes") != len(payload) or not hmac.compare_digest(
            str(expected.get("sha256") or ""), _digest(payload),
        ):
            raise TrustReleaseError("trust_release_file_digest_invalid")

    wanted_id = _sha256_value(expected_checkpoint_id, "expected_checkpoint_id")
    try:
        checkpoint = verify_public_checkpoint(
            root / CHECKPOINT_FILENAME, expected_checkpoint_id=wanted_id,
        )
    except FinalityCheckpointError as exc:
        raise TrustReleaseError(str(exc)) from exc
    declared = dict(manifest.get("checkpoint") or {})
    if not hmac.compare_digest(
        str(declared.get("checkpoint_id") or ""), checkpoint["checkpoint_id"],
    ) or not hmac.compare_digest(
        str(declared.get("validator_set_root") or ""), checkpoint["validator_set_root"],
    ):
        raise TrustReleaseError("trust_release_checkpoint_manifest_mismatch")

    verifier = (root / VERIFIER_FILENAME).read_bytes()
    if b"fetch(" in verifier or b"http://" in verifier or b"https://" in verifier:
        raise TrustReleaseError("trust_release_verifier_is_not_offline_only")
    if b"checkpoint-pin" not in verifier or b"pin!==cpId" not in verifier:
        raise TrustReleaseError("trust_release_verifier_independent_pin_gate_missing")
    return {
        "valid": True,
        "release_version": manifest["release_version"],
        "release_manifest_sha256": release_digest,
        "checkpoint_id": checkpoint["checkpoint_id"],
        "validator_set_root": checkpoint["validator_set_root"],
        "manifest_sha256": supplied_manifest_digest,
        "trust_anchor_source": "independently_supplied_checkpoint_id",
    }
