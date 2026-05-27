# backend/modules/aion_gateway/trust_reputation.py
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


TRUST_REPUTATION_VERSION = "aion.trust_reputation.v0.1"


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BusinessTrustSummary:
    business_id: str
    business_name: str
    vertical_key: str
    verified_completed_jobs: int = 0
    disputed_jobs: int = 0
    cancelled_jobs: int = 0
    failed_jobs: int = 0
    average_response_minutes: Optional[float] = None
    average_completion_hours: Optional[float] = None
    evidence_backed_completion_rate: float = 0.0
    proof_commitment_rate: float = 0.0
    proof_verification_success_rate: float = 0.0
    quote_reliability_rate: float = 0.0
    recovery_success_rate: float = 0.0
    explainability_notes: List[str] = field(default_factory=list)
    human_review_required: bool = True
    visibility_only: bool = True
    public_a2a_exposed: bool = False
    trust_summary_hash: str = ""

    def to_payload(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_version"] = TRUST_REPUTATION_VERSION
        data["trust_summary_hash"] = _stable_hash(
            {k: v for k, v in data.items() if k != "trust_summary_hash"}
        )
        return data


def _safe_rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(max(0.0, min(1.0, numerator / denominator)), 4)


def build_business_trust_summary(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    jobs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    records = list(jobs or [])

    completed = [j for j in records if j.get("status") == "completed"]
    verified_completed = [
        j for j in completed
        if j.get("proof_verified") is True and j.get("evidence_backed") is True
    ]

    disputed = [j for j in records if j.get("status") == "disputed"]
    cancelled = [j for j in records if j.get("status") == "cancelled"]
    failed = [j for j in records if j.get("status") == "failed"]

    response_times = [
        float(j["response_minutes"])
        for j in records
        if isinstance(j.get("response_minutes"), (int, float))
    ]
    completion_times = [
        float(j["completion_hours"])
        for j in completed
        if isinstance(j.get("completion_hours"), (int, float))
    ]

    evidence_backed = [j for j in completed if j.get("evidence_backed") is True]
    proof_committed = [j for j in completed if j.get("proof_committed") is True]
    proof_verified = [j for j in completed if j.get("proof_verified") is True]
    quote_reliable = [j for j in completed if j.get("quote_changed") is not True]
    recovery_success = [
        j for j in records
        if j.get("exception_recovery_attempted") is True and j.get("exception_recovery_success") is True
    ]
    recovery_attempted = [j for j in records if j.get("exception_recovery_attempted") is True]

    completed_count = len(completed)

    notes = [
        "Trust summary is explainable and derived from job-level preview records.",
        "Verified completions require both evidence-backed completion and proof verification.",
        "Fiat remains default; GlyphChain is used as proof infrastructure only.",
        "This summary is visibility-only and does not expose public A2A access.",
    ]

    summary = BusinessTrustSummary(
        business_id=str(business_id or "home_fixed"),
        business_name=str(business_name or "Home Fixed"),
        vertical_key=str(vertical_key or "home_repair"),
        verified_completed_jobs=len(verified_completed),
        disputed_jobs=len(disputed),
        cancelled_jobs=len(cancelled),
        failed_jobs=len(failed),
        average_response_minutes=round(sum(response_times) / len(response_times), 2) if response_times else None,
        average_completion_hours=round(sum(completion_times) / len(completion_times), 2) if completion_times else None,
        evidence_backed_completion_rate=_safe_rate(len(evidence_backed), completed_count),
        proof_commitment_rate=_safe_rate(len(proof_committed), completed_count),
        proof_verification_success_rate=_safe_rate(len(proof_verified), completed_count),
        quote_reliability_rate=_safe_rate(len(quote_reliable), completed_count),
        recovery_success_rate=_safe_rate(len(recovery_success), len(recovery_attempted)),
        explainability_notes=notes,
        human_review_required=True,
        visibility_only=True,
        public_a2a_exposed=False,
    ).to_payload()

    return {
        "ok": True,
        "status": "trust_summary_ready",
        "contract_version": TRUST_REPUTATION_VERSION,
        "trust_summary": summary,
        "trust_summary_hash": summary["trust_summary_hash"],
    }


def build_home_fixed_trust_summary_fixture() -> Dict[str, Any]:
    jobs = [
        {
            "job_id": "home_fixed_job_001",
            "status": "completed",
            "response_minutes": 18,
            "completion_hours": 6.5,
            "evidence_backed": True,
            "proof_committed": True,
            "proof_verified": True,
            "quote_changed": False,
        },
        {
            "job_id": "home_fixed_job_002",
            "status": "completed",
            "response_minutes": 31,
            "completion_hours": 4.0,
            "evidence_backed": True,
            "proof_committed": True,
            "proof_verified": True,
            "quote_changed": False,
            "exception_recovery_attempted": True,
            "exception_recovery_success": True,
        },
        {
            "job_id": "home_fixed_job_003",
            "status": "completed",
            "response_minutes": 45,
            "completion_hours": 12.0,
            "evidence_backed": True,
            "proof_committed": True,
            "proof_verified": False,
            "quote_changed": True,
        },
        {
            "job_id": "home_fixed_job_004",
            "status": "disputed",
            "response_minutes": 60,
            "exception_recovery_attempted": True,
            "exception_recovery_success": False,
        },
        {
            "job_id": "home_fixed_job_005",
            "status": "cancelled",
            "response_minutes": 22,
        },
        {
            "job_id": "home_fixed_job_006",
            "status": "failed",
            "response_minutes": 90,
        },
    ]

    return build_business_trust_summary(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        jobs=jobs,
    )
