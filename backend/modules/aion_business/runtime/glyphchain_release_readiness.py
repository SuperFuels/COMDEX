"""Fail-closed release evidence gate for GlyphChain and Legal production work."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


class GlyphChainReleaseReadinessError(ValueError):
    pass


SCHEMA_VERSION = "tessaris.glyphchain-legal-release-readiness.v1"
EVIDENCE_SCHEMA = "tessaris.glyphchain-legal-release-evidence.v1"
EVIDENCE_INVENTORY_SCHEMA = "tessaris.glyphchain-legal-release-evidence-inventory.v1"
TRUST_ROOTS_SCHEMA = "tessaris.glyphchain-legal-release-evidence-trust-roots.v2"
SIGNING_DOMAIN = "TESSARIS_GLYPHCHAIN_LEGAL_RELEASE_EVIDENCE_V1"
TRUST_ROOT_SIGNING_DOMAIN = "TESSARIS_GLYPHCHAIN_LEGAL_RELEASE_TRUST_ROOTS_V1"


def _task(
    workstream: str,
    description: str,
    roles: Sequence[str],
    artifact_kinds: Sequence[str],
    *,
    independent: bool = False,
) -> dict[str, Any]:
    return {
        "workstream": workstream,
        "description": description,
        "required_roles": list(roles),
        "required_artifact_kinds": list(artifact_kinds),
        "independent_required": bool(independent),
    }


TASKS: dict[str, dict[str, Any]] = {
    "LD-01": _task("live_delivery", "Production Resend callback and authenticated live delivery", ["delivery_operator"], ["resend_callback_configuration", "resend_authenticated_delivery_event"]),
    "LD-02": _task("live_delivery", "Microsoft 365 scopes and Message Trace provisioned", ["delivery_operator"], ["microsoft_scope_grant", "exchange_trace_access_grant"]),
    "LD-03": _task("live_delivery", "Microsoft draft/send and exact recipient trace validated", ["delivery_operator"], ["microsoft_draft_send_trace"]),
    "LD-04": _task("live_delivery", "Resend and Microsoft failure and retry cases exercised", ["delivery_operator"], ["delivery_failure_retry_matrix"]),
    "LD-05": _task("live_delivery", "Production delivery qualification report reviewed", ["delivery_operator", "security_reviewer"], ["production_delivery_qualification_report"], independent=True),
    "TR-01": _task("trust_publication", "Immutable checkpoint and verifier release published", ["release_publisher"], ["trust_release_manifest", "trust_release_publication_record"]),
    "TR-02": _task("trust_publication", "Checkpoint pin published through independent channel", ["independent_trust_publisher"], ["independent_checkpoint_pin_record"], independent=True),
    "TR-03": _task("trust_publication", "Clean-device private evidence verification completed", ["independent_verifier"], ["clean_device_verification_report"], independent=True),
    "NET-01": _task("distributed_network", "Malicious-validator response procedure approved", ["network_operator", "security_reviewer"], ["validator_response_approval", "validator_removal_exercise_report"], independent=True),
    "NET-02": _task("distributed_network", "Representative independent node profiles exercised", ["network_operator"], ["independent_node_qualification_report"]),
    "NET-03": _task("distributed_network", "Real NAT relay outage and partition conditions exercised", ["network_operator"], ["real_network_failure_report"]),
    "NET-04": _task("distributed_network", "Multi-device signed release activation completed", ["network_operator", "release_publisher"], ["multi_device_upgrade_activation_report"]),
    "NET-05": _task("distributed_network", "Production-like public relay independently validated", ["network_operator", "independent_verifier"], ["public_relay_validation_report", "relay_privacy_observation"], independent=True),
    "SEC-01": _task("security_recovery", "Independent registry and live lost-device recovery enforced", ["security_operator"], ["registry_deployment_record", "live_recovery_revocation_report"]),
    "SEC-02": _task("security_recovery", "Independent application-security review resolved", ["application_security_reviewer"], ["application_security_review", "application_security_findings_closure"], independent=True),
    "SEC-03": _task("security_recovery", "Independent consensus and cryptography review resolved", ["consensus_security_reviewer"], ["consensus_cryptography_review", "consensus_findings_closure"], independent=True),
    "SEC-04": _task("security_recovery", "Representative sustained multi-network soak passed", ["network_operator", "security_reviewer"], ["independent_multi_network_soak_report"], independent=True),
    "LEGAL-01": _task("qualified_legal_content", "Qualified reviewers appointed", ["legal_product_owner", "legal_reviewer"], ["qualified_reviewer_appointment"], independent=True),
    "LEGAL-02": _task("qualified_legal_content", "Customer agreements approved", ["legal_reviewer"], ["customer_agreement_qualified_approval"], independent=True),
    "LEGAL-03": _task("qualified_legal_content", "Supplier agreements approved", ["legal_reviewer"], ["supplier_agreement_qualified_approval"], independent=True),
    "LEGAL-04": _task("qualified_legal_content", "Contractor agreements approved", ["legal_reviewer"], ["contractor_agreement_qualified_approval"], independent=True),
    "LEGAL-05": _task("qualified_legal_content", "Employment documents approved", ["legal_reviewer"], ["employment_document_qualified_approval"], independent=True),
    "LEGAL-06": _task("qualified_legal_content", "Terms privacy and DPA wording approved", ["legal_reviewer"], ["terms_privacy_dpa_qualified_approval"], independent=True),
    "LEGAL-07": _task("qualified_legal_content", "Exact reviewed versions populated in encrypted library", ["legal_product_owner"], ["approved_template_library_manifest"]),
    "REL-01": _task("controlled_release", "Assurance and claim boundary published", ["release_publisher"], ["assurance_boundary_publication_record"]),
    "REL-02": _task("controlled_release", "Privacy participation and operator documents published", ["release_publisher"], ["operator_documentation_publication_record"]),
    "REL-03": _task("controlled_release", "Electronic-signature claims published exactly", ["release_publisher", "legal_product_owner"], ["electronic_signature_claim_publication"]),
    "REL-04": _task("controlled_release", "Internal multi-device deployment completed", ["deployment_operator"], ["internal_multi_device_deployment_report"]),
    "REL-05": _task("controlled_release", "Closed customer pilot completed", ["pilot_owner"], ["closed_customer_pilot_report"]),
    "REL-06": _task("controlled_release", "Pilot success metrics measured", ["metrics_reviewer"], ["pilot_metrics_report"]),
    "REL-07": _task("controlled_release", "Pilot findings resolved and retested", ["security_reviewer", "pilot_owner"], ["pilot_findings_closure_report"]),
    "REL-08": _task("controlled_release", "Release manifest frozen and trust independently pinned", ["release_publisher", "independent_trust_publisher"], ["frozen_release_manifest", "independent_release_pin_record"], independent=True),
    "REL-09": _task("controlled_release", "Final security Legal product and release approvals obtained", ["application_security_reviewer", "legal_product_owner", "release_approver"], ["final_security_approval", "final_legal_product_approval", "final_release_approval"], independent=True),
    "REL-10": _task("controlled_release", "Production release explicitly approved after all preceding gates", ["release_approver", "legal_product_owner", "application_security_reviewer"], ["preauthorization_readiness_report", "production_release_authorization"], independent=True),
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else _canonical(value)
    return sha256(payload).hexdigest()


def _release_digest(value: str) -> str:
    result = str(value or "").strip().lower().removeprefix("sha256:")
    if not re.fullmatch(r"[0-9a-f]{64}", result):
        raise GlyphChainReleaseReadinessError("release_manifest_sha256_invalid")
    return result


def _utc_time(value: Any) -> datetime:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        result = datetime.fromisoformat(text)
    except ValueError as exc:
        raise GlyphChainReleaseReadinessError("release_evidence_time_invalid") from exc
    if result.tzinfo is None:
        raise GlyphChainReleaseReadinessError("release_evidence_time_timezone_required")
    return result.astimezone(timezone.utc)


def evidence_sign_bytes(body: Mapping[str, Any]) -> bytes:
    return _canonical({"domain": SIGNING_DOMAIN, "evidence": dict(body)})


def sign_evidence(body: Mapping[str, Any], *, signer_id: str, private_key: Ed25519PrivateKey) -> dict[str, str]:
    return {
        "signer_id": str(signer_id),
        "signature_base64": base64.b64encode(private_key.sign(evidence_sign_bytes(body))).decode("ascii"),
    }


def trust_root_sign_bytes(body: Mapping[str, Any]) -> bytes:
    return _canonical({"domain": TRUST_ROOT_SIGNING_DOMAIN, "trust_root_inventory": dict(body)})


def sign_trust_root_inventory(
    body: Mapping[str, Any], *, authority_id: str, private_key: Ed25519PrivateKey,
) -> dict[str, str]:
    payload = trust_root_sign_bytes(body)
    return {
        "algorithm": "ed25519",
        "authority_id": str(authority_id),
        "signed_payload_sha256": sha256(payload).hexdigest(),
        "signature_base64": base64.b64encode(private_key.sign(payload)).decode("ascii"),
    }


def verify_trust_root_inventory(
    document: Mapping[str, Any], *, authority_public_key: Ed25519PublicKey,
) -> bool:
    value = dict(document)
    attestation = value.pop("attestation", None)
    if not isinstance(attestation, Mapping) or attestation.get("algorithm") != "ed25519":
        return False
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}",
        str(attestation.get("authority_id") or ""),
    ):
        return False
    payload = trust_root_sign_bytes(value)
    if not hmac.compare_digest(
        str(attestation.get("signed_payload_sha256") or ""),
        sha256(payload).hexdigest(),
    ):
        return False
    try:
        authority_public_key.verify(
            base64.b64decode(str(attestation.get("signature_base64") or ""), validate=True),
            payload,
        )
        return True
    except (ValueError, InvalidSignature):
        return False


class GlyphChainReleaseReadinessEvaluator:
    """Verify exact-release evidence without manufacturing an approval."""

    MAX_ENTRIES = len(TASKS)
    MAX_ATTESTATIONS_PER_ENTRY = 8
    MAX_ARTIFACTS_PER_ENTRY = 32
    MAX_ARTIFACT_ID_LENGTH = 160
    MAX_ARTIFACT_KIND_LENGTH = 120
    MAX_TRUST_ROOTS = 128
    MAX_ROLES_PER_TRUST_ROOT = 16
    MAX_PREAUTHORIZATION_REPORT_BYTES = 10_000_000
    MAX_TRUST_ROOT_INVENTORY_BYTES = 2_000_000

    def evaluate(
        self,
        *,
        release_manifest_sha256: str,
        evidence_entries: Sequence[Mapping[str, Any]],
        trust_root_inventory_bytes: bytes,
        trust_root_authority_public_key: Ed25519PublicKey | None = None,
        expected_trust_root_inventory_file_sha256: str | None = None,
        preauthorization_report_bytes: bytes | None = None,
        generated_at: str | None = None,
    ) -> dict[str, Any]:
        if (
            not isinstance(trust_root_inventory_bytes, bytes)
            or not trust_root_inventory_bytes
            or len(trust_root_inventory_bytes) > self.MAX_TRUST_ROOT_INVENTORY_BYTES
        ):
            raise GlyphChainReleaseReadinessError("trust_root_inventory_bytes_invalid")
        try:
            trust_root_document = json.loads(trust_root_inventory_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise GlyphChainReleaseReadinessError("trust_root_inventory_json_invalid") from exc
        if not isinstance(trust_root_document, Mapping):
            raise GlyphChainReleaseReadinessError("trust_root_inventory_object_required")
        if trust_root_document.get("schema_version") != TRUST_ROOTS_SCHEMA:
            raise GlyphChainReleaseReadinessError("trust_root_inventory_schema_invalid")
        trust_roots = trust_root_document.get("trust_roots")
        if not isinstance(trust_roots, Mapping):
            raise GlyphChainReleaseReadinessError("trust_root_inventory_roots_invalid")
        inventory_file_sha256 = sha256(trust_root_inventory_bytes).hexdigest()
        authenticated = False
        authority_key_id: str | None = None
        if trust_roots:
            expected = str(expected_trust_root_inventory_file_sha256 or "").lower()
            if not re.fullmatch(r"[0-9a-f]{64}", expected) or not hmac.compare_digest(
                expected, inventory_file_sha256
            ):
                raise GlyphChainReleaseReadinessError("trust_root_inventory_pin_invalid")
            if not isinstance(trust_root_authority_public_key, Ed25519PublicKey):
                raise GlyphChainReleaseReadinessError("trust_root_authority_key_required")
            if not verify_trust_root_inventory(
                trust_root_document,
                authority_public_key=trust_root_authority_public_key,
            ):
                raise GlyphChainReleaseReadinessError("trust_root_inventory_signature_invalid")
            authority_key_id = "ed25519:sha256:" + sha256(
                trust_root_authority_public_key.public_bytes_raw()
            ).hexdigest()
            authenticated = True
        return self._evaluate_verified(
            release_manifest_sha256=release_manifest_sha256,
            evidence_entries=evidence_entries,
            trust_roots=trust_roots,
            trust_roots_authenticated=authenticated,
            trust_root_inventory_file_sha256=inventory_file_sha256,
            trust_root_authority_key_id=authority_key_id,
            preauthorization_report_bytes=preauthorization_report_bytes,
            generated_at=generated_at,
        )

    def _evaluate_verified(
        self,
        *,
        release_manifest_sha256: str,
        evidence_entries: Sequence[Mapping[str, Any]],
        trust_roots: Mapping[str, Mapping[str, Any]],
        trust_roots_authenticated: bool = False,
        trust_root_inventory_file_sha256: str | None = None,
        trust_root_authority_key_id: str | None = None,
        preauthorization_report_bytes: bytes | None = None,
        generated_at: str | None = None,
    ) -> dict[str, Any]:
        release_digest = _release_digest(release_manifest_sha256)
        generated_value = generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        generated_time = _utc_time(generated_value)
        trust_root_inventory_errors = self._validate_trust_roots(trust_roots)
        (
            preauthorization_report_sha256,
            preauthorization_report_validated,
            preauthorization_report_errors,
        ) = self._validate_preauthorization_report_bytes(
            preauthorization_report_bytes,
            release_manifest_sha256=release_digest,
            trust_root_inventory_file_sha256=trust_root_inventory_file_sha256,
            trust_root_authority_key_id=trust_root_authority_key_id,
            evidence_inventory_sha256=_digest([
                entry for entry in evidence_entries
                if str(entry.get("task_id") or "").strip().upper() != "REL-10"
            ]),
            trust_roots_sha256=_digest(dict(trust_roots)),
        )
        if len(evidence_entries) > self.MAX_ENTRIES:
            raise GlyphChainReleaseReadinessError("release_evidence_entry_limit_exceeded")
        entries: dict[str, Mapping[str, Any]] = {}
        duplicate_ids: list[str] = []
        for raw in evidence_entries:
            task_id = str(raw.get("task_id") or "").strip().upper()
            if task_id in entries:
                duplicate_ids.append(task_id)
            else:
                entries[task_id] = raw

        task_results: dict[str, dict[str, Any]] = {}
        for task_id, requirement in TASKS.items():
            entry = entries.get(task_id)
            task_results[task_id] = self._evaluate_task(
                task_id=task_id,
                requirement=requirement,
                entry=entry,
                release_digest=release_digest,
                trust_roots=trust_roots,
                trust_roots_authenticated=trust_roots_authenticated,
                trust_root_inventory_errors=trust_root_inventory_errors,
                preauthorization_report_sha256=preauthorization_report_sha256,
                preauthorization_report_validated=preauthorization_report_validated,
                generated_time=generated_time,
            )
        unknown = sorted(task_id for task_id in entries if task_id not in TASKS)
        passed = sorted(task_id for task_id, item in task_results.items() if item["passed"])
        unmet = sorted(task_id for task_id, item in task_results.items() if not item["passed"])
        global_errors: list[str] = []
        if trust_roots and not trust_roots_authenticated:
            global_errors.append("trust_roots_authentication_required")
        global_errors.extend(trust_root_inventory_errors)
        all_passed = (
            len(passed) == len(TASKS)
            and not unknown
            and not duplicate_ids
            and trust_roots_authenticated
            and not trust_root_inventory_errors
            and not global_errors
        )
        preauthorization_ready = (
            len(passed) == len(TASKS) - 1
            and unmet == ["REL-10"]
            and "evidence_missing" in task_results["REL-10"]["errors"]
            and task_results["REL-10"]["evidence_body_sha256"] is None
            and not task_results["REL-10"]["attestation_signer_ids"]
            and not unknown
            and not duplicate_ids
            and trust_roots_authenticated
            and not trust_root_inventory_errors
            and not global_errors
        )
        result = (
            "ALL_RELEASE_GATES_EVIDENCED"
            if all_passed
            else "AWAITING_FINAL_RELEASE_AUTHORIZATION"
            if preauthorization_ready
            else "BLOCKED_EXTERNAL_GATES"
        )
        report: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_value,
            "release_manifest_sha256": release_digest,
            "evidence_inventory_sha256": _digest(list(evidence_entries)),
            "trust_roots_sha256": _digest(dict(trust_roots)),
            "trust_roots_authenticated": bool(trust_roots_authenticated),
            "trust_root_inventory_file_sha256": trust_root_inventory_file_sha256,
            "trust_root_authority_key_id": trust_root_authority_key_id,
            "preauthorization_report_sha256": preauthorization_report_sha256,
            "preauthorization_report_validated": bool(preauthorization_report_validated),
            "preauthorization_report_errors": preauthorization_report_errors,
            "preauthorization_ready": preauthorization_ready,
            "trust_root_inventory_errors": trust_root_inventory_errors,
            "global_errors": global_errors,
            "result": result,
            "production_release_authorized": all_passed,
            "claim_boundary": (
                "This evaluator verifies configured signatures, roles, independence flags, artifact digests "
                "and exact-release binding. It does not determine professional qualification, inspect an "
                "external system, or replace the human approvals named by each gate."
            ),
            "task_count": len(TASKS),
            "passed_count": len(passed),
            "unmet_count": len(unmet),
            "passed_task_ids": passed,
            "unmet_task_ids": unmet,
            "unknown_task_ids": unknown,
            "duplicate_task_ids": sorted(set(duplicate_ids)),
            "tasks": task_results,
        }
        report["report_sha256"] = _digest(report)
        return report

    def _evaluate_task(
        self,
        *,
        task_id: str,
        requirement: Mapping[str, Any],
        entry: Mapping[str, Any] | None,
        release_digest: str,
        trust_roots: Mapping[str, Mapping[str, Any]],
        trust_roots_authenticated: bool,
        trust_root_inventory_errors: Sequence[str],
        preauthorization_report_sha256: str | None,
        preauthorization_report_validated: bool,
        generated_time: datetime,
    ) -> dict[str, Any]:
        errors: list[str] = []
        valid_signers: dict[str, dict[str, Any]] = {}
        artifact_count = 0
        evidence_body_sha256: str | None = None
        artifact_manifest_sha256: str | None = None
        attestation_signer_ids: list[str] = []
        if entry is None:
            errors.append("evidence_missing")
        else:
            body = entry.get("body") if isinstance(entry.get("body"), Mapping) else {}
            evidence_body_sha256 = _digest(body)
            if body.get("schema_version") != EVIDENCE_SCHEMA:
                errors.append("evidence_schema_invalid")
            if str(body.get("task_id") or "").upper() != task_id:
                errors.append("evidence_task_binding_invalid")
            try:
                entry_release = _release_digest(str(body.get("release_manifest_sha256") or ""))
                if not hmac.compare_digest(entry_release, release_digest):
                    errors.append("evidence_release_binding_invalid")
            except GlyphChainReleaseReadinessError:
                errors.append("evidence_release_binding_invalid")
            if str(body.get("environment") or "").lower() != "production":
                errors.append("production_environment_evidence_required")
            if str(body.get("result") or "").upper() != "PASS":
                errors.append("evidence_result_not_pass")
            if not str(body.get("observed_at") or "").strip():
                errors.append("evidence_observed_at_required")
            else:
                try:
                    observed_time = _utc_time(body.get("observed_at"))
                    if observed_time > generated_time:
                        errors.append("evidence_observed_at_in_future")
                except GlyphChainReleaseReadinessError as exc:
                    errors.append(str(exc))
            statement = str(body.get("statement") or "").strip()
            if not statement:
                errors.append("evidence_statement_required")
            elif len(statement) > 4096:
                errors.append("evidence_statement_too_long")
            artifacts = body.get("artifacts") if isinstance(body.get("artifacts"), list) else []
            artifact_count = len(artifacts)
            artifact_manifest_sha256 = _digest(artifacts) if artifacts else None
            artifact_ids: set[str] = set()
            artifact_kinds: set[str] = set()
            artifact_hashes_by_kind: dict[str, set[str]] = {}
            if not artifacts or artifact_count > self.MAX_ARTIFACTS_PER_ENTRY:
                errors.append("evidence_artifacts_invalid")
            else:
                for artifact in artifacts:
                    artifact_id = str(artifact.get("artifact_id") or "").strip() if isinstance(artifact, Mapping) else ""
                    artifact_kind = str(artifact.get("kind") or "").strip() if isinstance(artifact, Mapping) else ""
                    if (
                        not isinstance(artifact, Mapping)
                        or not artifact_id
                        or len(artifact_id) > self.MAX_ARTIFACT_ID_LENGTH
                        or not artifact_kind
                        or len(artifact_kind) > self.MAX_ARTIFACT_KIND_LENGTH
                        or not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]*", artifact_id)
                        or not re.fullmatch(r"[a-z][a-z0-9_]*", artifact_kind)
                        or not re.fullmatch(
                            r"[0-9a-f]{64}", str(artifact.get("sha256") or "").lower(),
                        )
                    ):
                        errors.append("evidence_artifact_invalid")
                        break
                    if artifact_id in artifact_ids:
                        errors.append("evidence_artifact_id_duplicate")
                        break
                    artifact_ids.add(artifact_id)
                    artifact_kinds.add(artifact_kind)
                    artifact_hashes_by_kind.setdefault(artifact_kind, set()).add(
                        str(artifact.get("sha256") or "").lower()
                    )
                missing_artifact_kinds = sorted(
                    set(requirement["required_artifact_kinds"]) - artifact_kinds
                )
                if missing_artifact_kinds:
                    errors.append("required_artifacts_missing:" + ",".join(missing_artifact_kinds))
                if task_id == "REL-10":
                    expected_preauthorization = str(preauthorization_report_sha256 or "").lower()
                    if preauthorization_report_validated is not True:
                        errors.append("preauthorization_report_not_validated")
                    if not re.fullmatch(r"[0-9a-f]{64}", expected_preauthorization):
                        errors.append("preauthorization_report_required")
                    elif artifact_hashes_by_kind.get("preauthorization_readiness_report") != {
                        expected_preauthorization
                    }:
                        errors.append("preauthorization_report_binding_invalid")
            attestations = entry.get("attestations") if isinstance(entry.get("attestations"), list) else []
            if not trust_roots_authenticated:
                errors.append("trust_roots_not_authenticated")
            if trust_root_inventory_errors:
                errors.append("trust_root_inventory_invalid")
            if not attestations or len(attestations) > self.MAX_ATTESTATIONS_PER_ENTRY:
                errors.append("evidence_attestations_invalid")
            seen: set[str] = set()
            for attestation in attestations:
                if not isinstance(attestation, Mapping):
                    errors.append("evidence_attestation_invalid")
                    continue
                signer_id = str(attestation.get("signer_id") or "").strip()
                if (
                    not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", signer_id)
                    or signer_id in seen
                ):
                    errors.append("evidence_attestation_signer_duplicate_or_missing")
                    continue
                seen.add(signer_id)
                attestation_signer_ids.append(signer_id)
                root = trust_roots.get(signer_id)
                if not isinstance(root, Mapping):
                    errors.append(f"evidence_signer_untrusted:{signer_id}")
                    continue
                if not self._verify_signature(body, attestation, root):
                    errors.append(f"evidence_signature_invalid:{signer_id}")
                    continue
                root_roles = root.get("roles")
                if not isinstance(root_roles, list):
                    errors.append(f"evidence_signer_roles_invalid:{signer_id}")
                    continue
                roles = {str(role or "").strip() for role in root_roles if str(role or "").strip()}
                valid_signers[signer_id] = {
                    "roles": roles,
                    "independent": root.get("independent") is True,
                }

        required_roles = list(requirement["required_roles"])
        candidates = {
            role: sorted(signer_id for signer_id, signer in valid_signers.items() if role in signer["roles"])
            for role in required_roles
        }
        missing_roles = [role for role in required_roles if not candidates[role]]
        if missing_roles:
            errors.append("required_roles_missing:" + ",".join(missing_roles))
        role_assignment = self._assign_roles(required_roles, candidates, valid_signers, require_independent=False)
        if not missing_roles and role_assignment is None:
            errors.append("separation_of_duties_not_met")
        if requirement.get("independent_required"):
            independent_assignment = self._assign_roles(
                required_roles, candidates, valid_signers, require_independent=True,
            )
            if independent_assignment is None:
                errors.append("independent_attestation_required")
            else:
                role_assignment = independent_assignment
        return {
            "passed": not errors,
            "workstream": requirement["workstream"],
            "description": requirement["description"],
            "required_roles": required_roles,
            "required_artifact_kinds": list(requirement["required_artifact_kinds"]),
            "independent_required": requirement["independent_required"],
            "verified_role_signers": role_assignment or {},
            "evidence_body_sha256": evidence_body_sha256,
            "artifact_manifest_sha256": artifact_manifest_sha256,
            "artifact_count": artifact_count,
            "attestation_signer_ids": sorted(attestation_signer_ids),
            "errors": sorted(set(errors)),
        }

    @classmethod
    def _validate_preauthorization_report_bytes(
        cls,
        payload: bytes | None,
        *,
        release_manifest_sha256: str,
        trust_root_inventory_file_sha256: str | None,
        trust_root_authority_key_id: str | None,
        evidence_inventory_sha256: str,
        trust_roots_sha256: str,
    ) -> tuple[str | None, bool, list[str]]:
        if payload is None:
            return None, False, []
        if not isinstance(payload, bytes) or not payload or len(payload) > cls.MAX_PREAUTHORIZATION_REPORT_BYTES:
            return None, False, ["preauthorization_report_bytes_invalid"]
        file_sha256 = sha256(payload).hexdigest()
        try:
            report = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return file_sha256, False, ["preauthorization_report_json_invalid"]
        if not isinstance(report, Mapping):
            return file_sha256, False, ["preauthorization_report_object_required"]
        if not cls.verify_report(report):
            return file_sha256, False, ["preauthorization_report_digest_invalid"]
        if str(report.get("release_manifest_sha256") or "").lower() != release_manifest_sha256:
            return file_sha256, False, ["preauthorization_report_release_binding_invalid"]
        if (
            report.get("trust_root_inventory_file_sha256") != trust_root_inventory_file_sha256
            or report.get("trust_root_authority_key_id") != trust_root_authority_key_id
        ):
            return file_sha256, False, ["preauthorization_report_trust_binding_invalid"]
        if report.get("evidence_inventory_sha256") != evidence_inventory_sha256:
            return file_sha256, False, [
                "preauthorization_report_evidence_inventory_binding_invalid"
            ]
        if report.get("trust_roots_sha256") != trust_roots_sha256:
            return file_sha256, False, ["preauthorization_report_trust_inventory_binding_invalid"]
        task_results = report.get("tasks") if isinstance(report.get("tasks"), Mapping) else {}
        clean_state = (
            report.get("schema_version") == SCHEMA_VERSION
            and report.get("result") == "AWAITING_FINAL_RELEASE_AUTHORIZATION"
            and report.get("preauthorization_ready") is True
            and report.get("production_release_authorized") is False
            and report.get("task_count") == len(TASKS)
            and report.get("passed_count") == len(TASKS) - 1
            and report.get("unmet_count") == 1
            and report.get("passed_task_ids") == sorted(set(TASKS) - {"REL-10"})
            and report.get("unmet_task_ids") == ["REL-10"]
            and not report.get("unknown_task_ids")
            and not report.get("duplicate_task_ids")
            and not report.get("global_errors")
            and not report.get("trust_root_inventory_errors")
            and report.get("trust_roots_authenticated") is True
            and set(task_results) == set(TASKS)
            and all(
                isinstance(task_results.get(task_id), Mapping)
                and task_results[task_id].get("passed") is True
                for task_id in set(TASKS) - {"REL-10"}
            )
            and isinstance(task_results.get("REL-10"), Mapping)
            and task_results["REL-10"].get("passed") is False
            and "evidence_missing" in task_results["REL-10"].get("errors", [])
            and task_results["REL-10"].get("evidence_body_sha256") is None
            and not task_results["REL-10"].get("attestation_signer_ids")
        )
        if not clean_state:
            return file_sha256, False, ["preauthorization_report_not_clean_33_gate_state"]
        return file_sha256, True, []

    @classmethod
    def _validate_trust_roots(cls, trust_roots: Mapping[str, Mapping[str, Any]]) -> list[str]:
        errors: list[str] = []
        if len(trust_roots) > cls.MAX_TRUST_ROOTS:
            return ["trust_root_count_limit_exceeded"]
        allowed_roles = {role for task in TASKS.values() for role in task["required_roles"]}
        public_key_owners: dict[bytes, str] = {}
        for raw_signer_id, root in trust_roots.items():
            signer_id = str(raw_signer_id or "").strip()
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", signer_id):
                errors.append(f"trust_root_signer_id_invalid:{signer_id}")
                continue
            if not isinstance(root, Mapping):
                errors.append(f"trust_root_record_invalid:{signer_id}")
                continue
            try:
                public_key = base64.b64decode(str(root.get("public_key_base64") or ""), validate=True)
            except ValueError:
                public_key = b""
            if len(public_key) != 32:
                errors.append(f"trust_root_public_key_invalid:{signer_id}")
            elif public_key in public_key_owners:
                errors.append(
                    f"trust_root_public_key_duplicate:{public_key_owners[public_key]},{signer_id}"
                )
            else:
                public_key_owners[public_key] = signer_id
            roles = root.get("roles")
            if (
                not isinstance(roles, list)
                or not roles
                or len(roles) > cls.MAX_ROLES_PER_TRUST_ROOT
                or len(set(str(role) for role in roles)) != len(roles)
                or any(str(role) not in allowed_roles for role in roles)
            ):
                errors.append(f"trust_root_roles_invalid:{signer_id}")
            if not isinstance(root.get("independent"), bool):
                errors.append(f"trust_root_independence_invalid:{signer_id}")
        return sorted(set(errors))

    @staticmethod
    def _assign_roles(
        required_roles: Sequence[str],
        candidates: Mapping[str, Sequence[str]],
        signers: Mapping[str, Mapping[str, Any]],
        *,
        require_independent: bool,
    ) -> dict[str, str] | None:
        """Find an injective role assignment, including independence when required."""
        assignment: dict[str, str] = {}

        def visit(index: int, used: set[str]) -> bool:
            if index == len(required_roles):
                return not require_independent or any(
                    signers[signer_id].get("independent") is True
                    for signer_id in assignment.values()
                )
            role = required_roles[index]
            for signer_id in candidates.get(role, []):
                if signer_id in used:
                    continue
                assignment[role] = signer_id
                if visit(index + 1, used | {signer_id}):
                    return True
                assignment.pop(role, None)
            return False

        return dict(assignment) if visit(0, set()) else None

    @staticmethod
    def _verify_signature(
        body: Mapping[str, Any], attestation: Mapping[str, Any], root: Mapping[str, Any],
    ) -> bool:
        try:
            public = Ed25519PublicKey.from_public_bytes(
                base64.b64decode(str(root.get("public_key_base64") or ""), validate=True)
            )
            signature = base64.b64decode(
                str(attestation.get("signature_base64") or ""), validate=True,
            )
            public.verify(signature, evidence_sign_bytes(body))
            return True
        except (ValueError, InvalidSignature):
            return False

    @staticmethod
    def verify_report(report: Mapping[str, Any]) -> bool:
        value = dict(report)
        supplied = str(value.pop("report_sha256", ""))
        return bool(supplied) and hmac.compare_digest(supplied, _digest(value))

    @staticmethod
    def write_report(path: str | Path, report: Mapping[str, Any]) -> Path:
        requested = Path(path).expanduser()
        if requested.is_symlink():
            raise GlyphChainReleaseReadinessError("release_readiness_report_symlink_refused")
        output = Path(os.path.realpath(requested))
        if output.suffix.lower() != ".json":
            raise GlyphChainReleaseReadinessError("release_readiness_report_must_be_json")
        output.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(dict(report), indent=2, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            output.unlink(missing_ok=True)
            raise
        return output
