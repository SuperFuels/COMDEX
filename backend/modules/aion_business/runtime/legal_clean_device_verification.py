"""Bounded clean-device verification of a private Legal evidence package."""

from __future__ import annotations

from hashlib import sha256
import hmac
import io
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any, Mapping
import zipfile

from backend.modules.aion_business.runtime.legal_document_proof import LegalDocumentProofService
from backend.modules.consensus.trust_release import verify_trust_release


class CleanDeviceVerificationError(ValueError):
    pass


SCHEMA_VERSION = "tessaris.legal-clean-device-verification.v1"
MAX_PACKAGE_BYTES = 64 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 96 * 1024 * 1024
MAX_MEMBERS = 32
MAX_DOCUMENT_BYTES = 32 * 1024 * 1024
MAX_PROOF_BYTES = 16 * 1024 * 1024
MAX_CERTIFICATE_BYTES = 8 * 1024 * 1024


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _safe_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = Path(os.path.abspath(path))
    for component in (path, *path.parents):
        if component.is_symlink():
            raise CleanDeviceVerificationError("clean_device_verification_symlink_refused")
    return path


def _member(archive: zipfile.ZipFile, name: str, maximum: int) -> bytes:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise CleanDeviceVerificationError(f"clean_device_{name}_required") from exc
    if info.file_size > maximum:
        raise CleanDeviceVerificationError(f"clean_device_{name}_too_large")
    value = archive.read(info)
    if len(value) != info.file_size:
        raise CleanDeviceVerificationError(f"clean_device_{name}_size_mismatch")
    return value


def verify_clean_device_package(
    *,
    evidence_package: str | Path,
    trust_release_directory: str | Path,
    expected_checkpoint_id: str,
    expected_release_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Verify using only the private package, public release and external pin."""

    package_path = _safe_path(evidence_package)
    if not package_path.is_file() or package_path.stat().st_size > MAX_PACKAGE_BYTES:
        raise CleanDeviceVerificationError("clean_device_evidence_package_invalid")
    trust = verify_trust_release(
        trust_release_directory,
        expected_checkpoint_id=expected_checkpoint_id,
        expected_release_manifest_sha256=expected_release_manifest_sha256,
    )
    try:
        archive = zipfile.ZipFile(io.BytesIO(package_path.read_bytes()))
    except (zipfile.BadZipFile, OSError) as exc:
        raise CleanDeviceVerificationError("clean_device_evidence_package_invalid") from exc
    with archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(infos) > MAX_MEMBERS or len(names) != len(set(names)):
            raise CleanDeviceVerificationError("clean_device_evidence_member_set_invalid")
        if sum(item.file_size for item in infos) > MAX_UNCOMPRESSED_BYTES:
            raise CleanDeviceVerificationError("clean_device_evidence_uncompressed_limit_exceeded")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise CleanDeviceVerificationError("clean_device_evidence_member_path_invalid")
        proof_names = [name for name in names if name.endswith(".tessaris-proof")]
        if len(proof_names) != 1:
            raise CleanDeviceVerificationError("clean_device_exactly_one_proof_required")
        try:
            document = _member(archive, "document.txt", MAX_DOCUMENT_BYTES).decode("utf-8")
            proof = json.loads(_member(archive, proof_names[0], MAX_PROOF_BYTES))
            certificate = json.loads(
                _member(archive, "evidence-certificate.json", MAX_CERTIFICATE_BYTES)
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CleanDeviceVerificationError("clean_device_evidence_content_invalid") from exc
    if not isinstance(proof, Mapping) or not isinstance(certificate, Mapping):
        raise CleanDeviceVerificationError("clean_device_evidence_content_invalid")
    signers = certificate.get("signers")
    if not isinstance(signers, list) or len(signers) > 256:
        raise CleanDeviceVerificationError("clean_device_signer_evidence_invalid")

    with tempfile.TemporaryDirectory(prefix="tessaris-clean-device-") as scratch:
        verification = LegalDocumentProofService(
            scratch, chain_submission_enabled=False,
        ).verify_bundle(
            proof,
            document_content=document,
            private_signers=signers,
            trusted_validator_set_root=trust["validator_set_root"],
        )

    conditions = {
        "receipt_valid": verification.get("valid") is True,
        "document_matches": verification.get("document_matches") is True,
        "device_attestation_valid": verification.get("device_attestation_valid") is True,
        "private_signer_commitments_verified": (
            verification.get("private_signer_commitments_verified") is True
        ),
        "transaction_payload_verified": (
            verification.get("glyphchain_transaction_payload_verified") is True
        ),
        "merkle_inclusion_verified": (
            verification.get("glyphchain_inclusion_verified") is True
        ),
        "quorum_finality_trust_anchored": (
            verification.get("glyphchain_quorum_finality_verified") is True
            and verification.get("glyphchain_quorum_finality_assurance") == "TRUST_ANCHORED"
        ),
        "chain_finalized": verification.get("glyphchain_status") == "FINALIZED",
    }
    passed = all(conditions.values())
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result": "PASS" if passed else "FAIL",
        "valid": passed,
        "content_free": True,
        "evidence_package_sha256": sha256(package_path.read_bytes()).hexdigest(),
        "proof_id_commitment": sha256(
            str(verification.get("proof_id") or "").encode("utf-8")
        ).hexdigest(),
        "trust_release": trust,
        "checks": conditions,
        "errors": [sha256(str(item).encode("utf-8")).hexdigest() for item in verification.get("errors") or []],
        "claim_boundary": (
            "This proves local cryptographic consistency against the independently "
            "supplied checkpoint pin; it does not prove legal enforceability, signer "
            "identity beyond policy, qualified-signature status or public availability."
        ),
    }
    report["report_sha256"] = sha256(_canonical(report)).hexdigest()
    return report


def write_clean_device_report(output: str | Path, report: Mapping[str, Any]) -> Path:
    path = _safe_path(output)
    if path.suffix.lower() != ".json":
        raise CleanDeviceVerificationError("clean_device_report_must_be_json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise CleanDeviceVerificationError("clean_device_report_already_exists")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(report), indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return path


def verify_clean_device_report(report: Mapping[str, Any]) -> bool:
    value = dict(report)
    supplied = str(value.pop("report_sha256", ""))
    return bool(supplied) and hmac.compare_digest(
        supplied, sha256(_canonical(value)).hexdigest(),
    )
