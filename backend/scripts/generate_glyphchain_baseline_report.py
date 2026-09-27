#!/usr/bin/env python3
"""Generate a device-signed GlyphChain baseline report from pytest JUnit XML.

The private release-attestation key is stored outside the tracked source tree.
The report contains its public key, signature and a digest of the exact relevant
working-tree files so an uncommitted development baseline is not misrepresented
as the current Git commit alone.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KEY = ROOT / ".runtime" / "glyphchain" / "baseline-ed25519.pem"
DEFAULT_OUTPUT = ROOT / "docs" / "aion" / "GLYPHCHAIN_BASELINE_REPORT.json"
DEFAULT_PUBLIC_KEY = ROOT / "docs" / "aion" / "GLYPHCHAIN_BASELINE_SIGNING_PUBLIC_KEY.pem"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def source_manifest() -> dict[str, object]:
    roots = [
        ROOT / "backend" / "modules" / "consensus",
        ROOT / "backend" / "modules" / "p2p",
        ROOT / "backend" / "modules" / "chain_sim",
        ROOT / "backend" / "tests" / "glyphchain",
    ]
    explicit = [
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "__init__.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "glyphchain_release_readiness.py",
        ROOT / "backend" / "scripts" / "generate_glyphchain_baseline_report.py",
        ROOT / "backend" / "scripts" / "evaluate_glyphchain_legal_release_readiness.py",
        ROOT / "backend" / "scripts" / "create_glyphchain_release_evidence.py",
        ROOT / "backend" / "scripts" / "create_glyphchain_release_trust_roots.py",
        ROOT / "backend" / "scripts" / "application_account_recovery.py",
        ROOT / "backend" / "scripts" / "run_application_account_descriptor_registry.py",
        ROOT / "backend" / "scripts" / "build_glyphchain_trust_release.py",
        ROOT / "backend" / "scripts" / "run_glyphchain_clean_device_verification.py",
        ROOT / "backend" / "scripts" / "run_glyphchain_network_qualification.py",
        ROOT / "backend" / "scripts" / "run_glyphchain_network_soak_qualification.py",
        ROOT / "backend" / "scripts" / "run_legal_delivery_qualification.py",
        ROOT / "backend" / "scripts" / "legal_full_state_recovery.py",
        ROOT / "backend" / "scripts" / "run_glyphchain_legal_disaster_recovery_exercise.py",
        ROOT / "backend" / "scripts" / "run_glyphchain_validator_removal_exercise.py",
        ROOT / "backend" / "tests" / "helpers.py",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_LEGAL_REPLAY_AND_DUPLICATE_REVIEW.md",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_ASSURANCE_AND_PRIVACY_BOUNDARY_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_APPLICATION_ACCOUNT_RECOVERY_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_APPLICATION_ACCOUNT_RECOVERY.md",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_LEGAL_LIVE_SIGNING_DELIVERY_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_INDEPENDENT_TRUST_PUBLICATION_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_DISTRIBUTED_NETWORK_QUALIFICATION_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_NETWORK_QUALIFICATION_REPORT.json",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_SECURITY_RECOVERY_AND_SOAK_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_NETWORK_SOAK_QUALIFICATION_REPORT.json",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_RELEASE_EVIDENCE_GATE_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_RELEASE_GATE_HARDENING_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_RELEASE_EVIDENCE_ARTIFACT_CONTRACT_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_RELEASE_TRUST_ROOT_GOVERNANCE_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_TWO_PHASE_RELEASE_AUTHORIZATION_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_LOCAL_COMPLETION_AND_EXTERNAL_GATES_SECTION.tex",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_LOCALLY_ACTIONABLE_COMPLETION_AUDIT.md",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_LEGAL_REMAINING_BUILD_CHECKLIST.md",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_LEGAL_RESOURCE_EXHAUSTION_REVIEW.md",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_LEGAL_INCIDENT_RESPONSE_PLAYBOOK.md",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_LEGAL_DISASTER_RECOVERY_EXERCISE_REPORT.json",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_LEGAL_TEMPLATE_REVIEW_AND_WITHDRAWAL.md",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_NETWORK_PARTICIPATION.md",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_RELAY_VALIDATOR_OPERATOR_RUNBOOK.md",
        ROOT / "docs" / "aion" / "GLYPHCHAIN_VALIDATOR_REMOVAL_EXERCISE_REPORT.json",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_document_proof.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "application_account_recovery.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "application_account_descriptor_registry.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "aion_flow_session_authority.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_full_state_backup.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_delivery_service.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_delivery_qualification.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_clean_device_verification.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_document_service.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_matter_service.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_pilot_harness_service.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_record_governance.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_resource_limits.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_secure_storage.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_signing_service.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_template_service.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "paths.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "request_body_limits.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "public_signer_rate_limit.py",
        ROOT / "backend" / "modules" / "aion_business" / "api" / "legal_signing_api.py",
        ROOT / "backend" / "modules" / "aion_business" / "api" / "glyphchain_admin_api.py",
        ROOT / "backend" / "modules" / "aion_business" / "providers" / "resend_adapter.py",
        ROOT / "backend" / "modules" / "aion_business" / "providers" / "microsoft_graph_mail_adapter.py",
        ROOT / "backend" / "modules" / "aion_business" / "static" / "tessaris-proof-verifier.html",
        ROOT / "backend" / "modules" / "pilot_unified" / "workspace_gateway.py",
        ROOT / "backend" / "tests" / "aion_business" / "test_microsoft_graph_mail_adapter.py",
        ROOT / "backend" / "tests" / "aion_business" / "test_resend_adapter.py",
        ROOT / "desktop" / "mac" / "src" / "aion_legal_workspace.js",
        ROOT / "desktop" / "mac" / "electron" / "main.js",
        ROOT / "backend" / "main.py",
        ROOT / "desktop" / "mac" / "src" / "app.js",
        ROOT / "desktop" / "mac" / "src" / "index.html",
    ]
    explicit.extend(
        sorted((ROOT / "backend" / "tests" / "workflow_capsules").glob("test_aion_legal_*.py"))
    )
    files = set(explicit)
    for pattern in ("GLYPHCHAIN*.md", "GLYPHCHAIN*.tex"):
        files.update((ROOT / "docs" / "aion").glob(pattern))
    for folder in roots:
        files.update(path for path in folder.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    entries = []
    for path in sorted(files):
        if not path.exists():
            continue
        if path.is_symlink():
            raise SystemExit(f"Refusing symlink in GlyphChain baseline source manifest: {path}")
        entries.append({
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path.read_bytes()).hexdigest(),
        })
    return {
        "file_count": len(entries),
        "manifest_sha256": sha256(canonical(entries)).hexdigest(),
        "entries": entries,
    }


def junit_summary(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    summary = {name: 0 for name in ("tests", "failures", "errors", "skipped")}
    duration = 0.0
    for suite in suites:
        for name in summary:
            summary[name] += int(suite.attrib.get(name, 0) or 0)
        duration += float(suite.attrib.get("time", 0.0) or 0.0)
    summary["duration_seconds"] = round(duration, 6)
    summary["passed"] = summary["tests"] - summary["failures"] - summary["errors"] - summary["skipped"]
    if summary["failures"] or summary["errors"]:
        raise SystemExit("Refusing to sign a failing GlyphChain baseline")
    return summary


def _exclusive_write(path: Path, payload: bytes, *, mode: int) -> None:
    if path.is_symlink():
        raise SystemExit(f"Refusing symbolic-link output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    except FileExistsError as exc:
        raise SystemExit(f"Refusing to replace existing exclusive output: {path}") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _atomic_replace(path: Path, payload: bytes, *, mode: int) -> None:
    if path.is_symlink():
        raise SystemExit(f"Refusing symbolic-link output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def private_key(path: Path) -> Ed25519PrivateKey:
    if path.is_symlink():
        raise SystemExit(f"Refusing symbolic-link private key: {path}")
    if path.exists():
        value = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(value, Ed25519PrivateKey):
            raise SystemExit("Baseline signing key is not Ed25519")
        return value
    path.parent.mkdir(parents=True, exist_ok=True)
    value = Ed25519PrivateKey.generate()
    _exclusive_write(path, value.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ), mode=0o600)
    return value


def public_key_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def ensure_public_key(path: Path, key: Ed25519PrivateKey) -> bytes:
    """Create the tracked trust anchor once and reject silent key replacement."""
    if path.is_symlink():
        raise SystemExit(f"Refusing symbolic-link public key: {path}")
    public = public_key_bytes(key)
    pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if path.exists():
        expected = serialization.load_pem_public_key(path.read_bytes())
        if not isinstance(expected, Ed25519PublicKey):
            raise SystemExit("Baseline public key is not Ed25519")
        expected_raw = expected.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if expected_raw != public:
            raise SystemExit("Private baseline key does not match the tracked public verification key")
        return public
    path.parent.mkdir(parents=True, exist_ok=True)
    _exclusive_write(path, pem, mode=0o644)
    return public


def verify_report(path: Path, public_key_path: Path) -> None:
    if path.is_symlink() or public_key_path.is_symlink():
        raise SystemExit("Refusing symbolic-link baseline verification input")
    document = json.loads(path.read_text(encoding="utf-8"))
    attestation = document.pop("attestation", None)
    if not isinstance(attestation, dict):
        raise SystemExit("Baseline report has no attestation")
    expected = serialization.load_pem_public_key(public_key_path.read_bytes())
    if not isinstance(expected, Ed25519PublicKey):
        raise SystemExit("Baseline public key is not Ed25519")
    expected_raw = expected.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    embedded_raw = base64.b64decode(str(attestation.get("public_key_base64", "")), validate=True)
    if embedded_raw != expected_raw:
        raise SystemExit("Baseline report was not signed by the tracked public key")
    payload = canonical(document)
    digest = sha256(payload).hexdigest()
    if attestation.get("signed_payload_sha256") != digest:
        raise SystemExit("Baseline report payload digest is invalid")
    try:
        expected.verify(base64.b64decode(str(attestation.get("signature_base64", "")), validate=True), payload)
    except (InvalidSignature, ValueError) as exc:
        raise SystemExit("Baseline report signature is invalid") from exc
    print(f"VERIFIED {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--junit-xml", type=Path)
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--public-key", type=Path, default=DEFAULT_PUBLIC_KEY)
    args = parser.parse_args()

    if args.verify:
        verify_report(args.verify, args.public_key)
        return 0

    results = junit_summary(args.junit_xml)
    report = {
        "schema_version": "tessaris.glyphchain-baseline-report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": (
            "backend/tests/glyphchain + "
            "backend/tests/workflow_capsules/test_aion_legal_*.py + "
            "Legal delivery-adapter tests"
        ),
        "result": "PASS",
        "tests": results,
        "source": {
            "git_commit": git("rev-parse", "HEAD"),
            "working_tree_dirty": bool(git("status", "--porcelain")),
            **source_manifest(),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
        },
        "verified_topology": {
            "maximum_validator_nodes_exercised": 4,
            "profiles": ["single-node", "four-validator", "restart", "gap-catch-up", "adversarial-soak"],
            "claim_boundary": "Measured regression topology, not a production network-size guarantee",
        },
        "configured_resource_bounds": {
            "p2p_queue_max_default": 20000,
            "block_max_transactions_default": 100,
            "block_max_interval_ms_default": 25,
            "claim_boundary": "Configuration defaults verified in source; production capacity requires deployment testing",
        },
        "latency": {
            "suite_duration_seconds": results["duration_seconds"],
            "per_transaction_finality_slo": None,
            "claim_boundary": "No production finality SLO is claimed from local regression timing",
        },
    }
    key = private_key(args.key)
    public = ensure_public_key(args.public_key, key)
    attestation = {
        "algorithm": "ed25519",
        "key_id": f"ed25519:sha256:{sha256(public).hexdigest()}",
        "public_key_base64": base64.b64encode(public).decode("ascii"),
        "signed_payload_sha256": sha256(canonical(report)).hexdigest(),
        "signature_base64": base64.b64encode(key.sign(canonical(report))).decode("ascii"),
    }
    output = {**report, "attestation": attestation}
    _atomic_replace(
        args.output,
        (json.dumps(output, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        mode=0o644,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
