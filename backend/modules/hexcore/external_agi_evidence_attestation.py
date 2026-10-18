from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


SCHEMA_VERSION = "aion.external.agi_evidence_attestation.v1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _unsigned(envelope: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in envelope.items() if key != "signature_ed25519_base64"}


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _contains_all(actual: Sequence[str], required: Sequence[str]) -> bool:
    return set(required).issubset(set(actual))


def verify_external_attestation(
    *,
    envelope: Mapping[str, Any],
    handoff: Mapping[str, Any],
    evaluator_public_key_pem: bytes,
) -> Dict[str, Any]:
    errors: list[str] = []
    signature_valid = False
    try:
        public_key = serialization.load_pem_public_key(evaluator_public_key_pem)
        if not isinstance(public_key, Ed25519PublicKey):
            errors.append("PUBLIC_KEY_NOT_ED25519")
        else:
            signature = base64.b64decode(envelope.get("signature_ed25519_base64", ""), validate=True)
            public_key.verify(signature, _canonical_bytes(_unsigned(envelope)))
            signature_valid = True
    except (ValueError, TypeError, InvalidSignature):
        errors.append("SIGNATURE_INVALID")

    if envelope.get("schema_version") != SCHEMA_VERSION:
        errors.append("SCHEMA_VERSION_INVALID")
    if not envelope.get("evaluator_id"):
        errors.append("EVALUATOR_ID_MISSING")
    if envelope.get("independent_of_aion_development") is not True:
        errors.append("INDEPENDENCE_NOT_ATTESTED")
    if envelope.get("registry_commitment") != handoff.get("registry_commitment"):
        errors.append("REGISTRY_COMMITMENT_MISMATCH")
    if envelope.get("artifact_manifest_commitment") != handoff.get("artifact_manifest_commitment"):
        errors.append("ARTIFACT_MANIFEST_COMMITMENT_MISMATCH")

    preregistration = envelope.get("preregistration", {})
    for field in (
        "sealed_portfolio_commitment",
        "delayed_outcome_commitment",
        "human_rater_panel_commitment",
        "matched_budget_commitment",
        "answer_reveal_commitment",
    ):
        if not _is_sha256(preregistration.get(field)):
            errors.append(f"INVALID_{field.upper()}")

    audit = envelope.get("audit", {})
    if not _contains_all(
        audit.get("portfolio_families", []), handoff.get("required_portfolio_families", [])
    ):
        errors.append("PORTFOLIO_FAMILIES_INCOMPLETE")
    if not _contains_all(audit.get("matched_systems", []), handoff.get("required_matched_systems", [])):
        errors.append("MATCHED_SYSTEMS_INCOMPLETE")
    audit_flags = audit.get("audit_flags", {})
    for field in handoff.get("required_audit_fields", []):
        if audit_flags.get(field) is not True:
            errors.append(f"AUDIT_FAILED_{field.upper()}")

    required_gates = {
        "broad_domain_transfer",
        "autonomous_long_project_decomposition",
        "independently_owned_consequence_learning",
        "continual_improvement_without_forgetting",
        "natural_multimodal_physical_grounding",
        "social_commonsense_creative_judgment",
        "tool_and_representation_invention",
        "safe_abstention_and_human_escalation",
        "matched_frontier_and_human_comparison",
        "independent_reproducibility",
    }
    gate_rows = envelope.get("gate_results", [])
    gate_by_id = {
        row.get("gate_id"): row for row in gate_rows if isinstance(row, Mapping) and row.get("gate_id")
    }
    missing_gates = sorted(required_gates - set(gate_by_id))
    if missing_gates:
        errors.append("GATE_RESULTS_INCOMPLETE:" + ",".join(missing_gates))
    for gate_id in sorted(required_gates & set(gate_by_id)):
        row = gate_by_id[gate_id]
        if row.get("passed") is not True:
            errors.append(f"GATE_NOT_PASSED_{gate_id.upper()}")
        if not _is_sha256(row.get("evidence_commitment")):
            errors.append(f"GATE_EVIDENCE_INVALID_{gate_id.upper()}")

    reproduction = envelope.get("reproduction", {})
    if reproduction.get("independent_runs", 0) < 1:
        errors.append("INDEPENDENT_REPRODUCTION_MISSING")
    if reproduction.get("artifact_hashes_verified") is not True:
        errors.append("ARTIFACT_HASH_REPRODUCTION_FAILED")
    if reproduction.get("complete_logs_published") is not True:
        errors.append("REPRODUCTION_LOGS_MISSING")

    verified = signature_valid and not errors
    return {
        "schema_version": "aion.external.agi_evidence_attestation_verdict.v1",
        "evaluator_id": envelope.get("evaluator_id"),
        "signature_valid": signature_valid,
        "all_ten_gates_externally_attested": verified,
        "external_certification_accepted": verified,
        "errors": errors,
        "boundary": (
            "This verifier authenticates the evaluator's signed claims and checks the frozen "
            "handoff contract. It cannot establish that the evaluator is genuinely independent "
            "or that reported measurements are scientifically valid without public audit and "
            "reproduction of the underlying artifacts."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--envelope", type=Path, required=True)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--verdict", type=Path, required=True)
    args = parser.parse_args()
    verdict = verify_external_attestation(
        envelope=json.loads(args.envelope.read_text(encoding="utf-8")),
        handoff=json.loads(args.handoff.read_text(encoding="utf-8")),
        evaluator_public_key_pem=args.public_key.read_bytes(),
    )
    args.verdict.parent.mkdir(parents=True, exist_ok=True)
    args.verdict.write_text(json.dumps(verdict, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(verdict, indent=2, sort_keys=True))
    raise SystemExit(0 if verdict["external_certification_accepted"] else 2)


if __name__ == "__main__":
    main()

