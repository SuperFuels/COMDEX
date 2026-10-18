from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Tuple

from backend.modules.connectors.priority_provider_catalog import CURRENT_READINESS, get_priority_provider_catalog


@dataclass(frozen=True)
class ReleaseGate:
    stage: str
    required_evidence: Tuple[str, ...]


RELEASE_GATES: Tuple[ReleaseGate, ...] = (
    ReleaseGate("contract_ready", ("contract_sha256",)),
    ReleaseGate("knowledge_ready", ("contract_sha256", "knowledge_assessment_receipt")),
    ReleaseGate("adapter_ready", ("contract_sha256", "knowledge_assessment_receipt", "adapter_contract_receipt", "dry_run_receipt")),
    ReleaseGate("credential_ready", ("contract_sha256", "knowledge_assessment_receipt", "adapter_contract_receipt", "dry_run_receipt", "credential_health_receipt")),
    ReleaseGate("sandbox_verified", ("contract_sha256", "knowledge_assessment_receipt", "adapter_contract_receipt", "dry_run_receipt", "credential_health_receipt", "sandbox_write_receipt")),
    ReleaseGate("live_verified", ("contract_sha256", "knowledge_assessment_receipt", "adapter_contract_receipt", "dry_run_receipt", "credential_health_receipt", "sandbox_write_receipt", "approved_live_action_receipt", "provider_readback_receipt", "failure_test_receipt", "revocation_test_receipt")),
)


def _present(evidence: Dict[str, Any], keys: Iterable[str]) -> bool:
    return all(bool(evidence.get(key)) for key in keys)


def evaluate_provider_release(tool_id: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    if tool_id not in get_priority_provider_catalog():
        return {"tool_id": tool_id, "valid": False, "stage": "unregistered", "missing": ["registered_provider_manifest"], "live_execution_allowed": False}

    achieved = "catalogued"
    for gate in RELEASE_GATES:
        if _present(evidence, gate.required_evidence):
            achieved = gate.stage
        else:
            break

    next_gate = next((gate for gate in RELEASE_GATES if not _present(evidence, gate.required_evidence)), None)
    missing = [] if next_gate is None else [key for key in next_gate.required_evidence if not evidence.get(key)]
    return {
        "tool_id": tool_id,
        "valid": True,
        "stage": achieved,
        "missing": missing,
        "live_execution_allowed": achieved == "live_verified",
        "claim_boundary": "Live verification requires an approved real action, provider read-back, and passing failure and revocation tests.",
    }


def build_priority_release_report(evidence_by_tool: Dict[str, Dict[str, Any]] | None = None) -> Dict[str, Any]:
    evidence_by_tool = evidence_by_tool or {}
    providers = {tool_id: evaluate_provider_release(tool_id, evidence_by_tool.get(tool_id, {})) for tool_id in get_priority_provider_catalog()}
    return {
        "schema_version": "aion.provider_release_report.v1",
        "providers": providers,
        "live_verified_count": sum(item["live_execution_allowed"] for item in providers.values()),
        "declared_repository_readiness": CURRENT_READINESS,
    }
