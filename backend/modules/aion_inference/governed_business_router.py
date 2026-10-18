"""End-to-end governed routing over verified knowledge and model capability gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .adaptive_runtime import AdaptiveInferenceRuntime
from .business_map import render_supplier_payment_controls
from .candidate_supplier_intent_normalizer import (
    CONTRACT_SHA256 as SUPPLIER_NORMALIZER_CONTRACT_SHA256,
    canonicalize_supplier_extraction_request,
)
from .task_model_router import select_task_model
from .verified_quotation import draft_verified_quotation
from .verified_supplier_extraction import extract_verified_supplier_fields


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _request_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _is_supplier_controls_question(text: str) -> bool:
    lowered = text.casefold()
    required = (
        re.search(r"\bsupplier\b", lowered),
        re.search(r"\b(?:pay|paying|payments?)\b", lowered),
        re.search(r"\bcontrols?\b", lowered),
        re.search(r"\brisk\b", lowered),
        re.search(r"\bevidence\b", lowered),
    )
    prohibited_action = re.search(
        r"\b(?:execute|send|make|approve|authorise|authorize|transfer)\b.{0,40}\bpayments?\b",
        lowered,
    )
    return all(required) and prohibited_action is None


@dataclass(frozen=True)
class GovernedBusinessOutcome:
    route: str
    model: str | None
    model_call_required: bool
    human_review_required: bool
    task_completed: bool
    answer: str | None
    glyph_address: str
    fallback_prompt: str | None
    proof_receipt: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GovernedBusinessRouter:
    """Prefer verified routes and quarantine exact contracts with proven failures."""

    def __init__(
        self,
        *,
        runtime: AdaptiveInferenceRuntime,
        cartridge_path: Path,
        signature_path: Path,
        trust_anchors_path: Path,
        failed_model_contracts: Mapping[str, str] | None = None,
    ) -> None:
        self.runtime = runtime
        self.cartridge_path = cartridge_path
        self.signature_path = signature_path
        self.trust_anchors_path = trust_anchors_path
        self.failed_model_contracts = dict(failed_model_contracts or {})

    @staticmethod
    def _seal(payload: Mapping[str, Any]) -> dict[str, Any]:
        receipt = dict(payload)
        receipt["proof_receipt_sha256"] = _canonical_sha256(receipt)
        return receipt

    def route(self, public_request: str) -> GovernedBusinessOutcome:
        request_hash = _request_sha256(public_request)
        if request_hash in self.failed_model_contracts:
            source_hash = self.failed_model_contracts[request_hash]
            receipt = self._seal({
                "schema_version": "aion.negative_capability_route_receipt.v1",
                "request_sha256": request_hash,
                "failed_quality_evidence_sha256": source_hash,
                "route": "human_review_required",
                "reason": "exact_contract_previously_failed_quality_gate",
                "model_calls": 0,
                "task_completed": False,
            })
            return GovernedBusinessOutcome(
                route="human_review_required",
                model=None,
                model_call_required=False,
                human_review_required=True,
                task_completed=False,
                answer=None,
                glyph_address=f"glyph:sha256:{request_hash}",
                fallback_prompt=None,
                proof_receipt=receipt,
            )

        if _is_supplier_controls_question(public_request):
            policy = render_supplier_payment_controls(
                cartridge_path=self.cartridge_path,
                signature_path=self.signature_path,
                trust_anchors_path=self.trust_anchors_path,
            )
            receipt = self._seal({
                "schema_version": "aion.governed_business_route_receipt.v1",
                "request_sha256": request_hash,
                "route": policy.route,
                "business_map_proof_receipt_sha256": policy.proof_receipt[
                    "proof_receipt_sha256"
                ],
                "model_calls": 0,
                "task_completed": True,
                "payment_execution_allowed": False,
            })
            return GovernedBusinessOutcome(
                route=policy.route,
                model=None,
                model_call_required=False,
                human_review_required=False,
                task_completed=True,
                answer=policy.answer,
                glyph_address=str(policy.proof_receipt["glyph_address"]),
                fallback_prompt=None,
                proof_receipt=receipt,
            )

        quotation = draft_verified_quotation(public_request)
        if quotation is not None:
            receipt = self._seal({
                "schema_version": "aion.governed_business_route_receipt.v1",
                "request_sha256": request_hash,
                "route": quotation.route,
                "quotation_proof_receipt_sha256": quotation.proof_receipt[
                    "proof_receipt_sha256"
                ],
                "model_calls": 0,
                "task_completed": True,
                "human_approval_required": True,
                "send_allowed": False,
                "payment_allowed": False,
            })
            return GovernedBusinessOutcome(
                route=quotation.route,
                model=None,
                model_call_required=False,
                human_review_required=True,
                task_completed=True,
                answer=quotation.answer,
                glyph_address=f"glyph:sha256:{request_hash}",
                fallback_prompt=None,
                proof_receipt=receipt,
            )

        canonical_request = canonicalize_supplier_extraction_request(public_request)
        extraction = (
            extract_verified_supplier_fields(canonical_request)
            if canonical_request is not None else None
        )
        if extraction is not None:
            answer = json.dumps(
                dict(extraction.fields), sort_keys=True, separators=(",", ":")
            )
            receipt = self._seal({
                "schema_version": "aion.governed_business_route_receipt.v1",
                "request_sha256": request_hash,
                "canonical_request_sha256": _request_sha256(canonical_request),
                "supplier_normalizer_contract_sha256": (
                    SUPPLIER_NORMALIZER_CONTRACT_SHA256
                ),
                "normalization_applied": canonical_request != " ".join(public_request.split()),
                "route": extraction.route,
                "extraction_proof_receipt_sha256": extraction.proof_receipt[
                    "proof_receipt_sha256"
                ],
                "model_calls": 0,
                "task_completed": True,
                "payment_execution_allowed": False,
            })
            return GovernedBusinessOutcome(
                route=extraction.route,
                model=None,
                model_call_required=False,
                human_review_required=False,
                task_completed=True,
                answer=answer,
                glyph_address=f"glyph:sha256:{request_hash}",
                fallback_prompt=None,
                proof_receipt=receipt,
            )

        adaptive = self.runtime.route(public_request)
        decision = select_task_model(adaptive, public_request)
        completed = not adaptive.model_call_required
        receipt = self._seal({
            "schema_version": "aion.governed_business_route_receipt.v1",
            "request_sha256": request_hash,
            "route": decision.route,
            "task_model_decision_sha256": decision.decision_sha256,
            "adaptive_proof_receipt_sha256": adaptive.proof_receipt[
                "proof_receipt_sha256"
            ],
            "model_calls": 1 if adaptive.model_call_required else 0,
            "task_completed": completed,
        })
        return GovernedBusinessOutcome(
            route=decision.route,
            model=decision.model,
            model_call_required=adaptive.model_call_required,
            human_review_required=False,
            task_completed=completed,
            answer=adaptive.answer,
            glyph_address=adaptive.glyph_address,
            fallback_prompt=adaptive.fallback_prompt,
            proof_receipt=receipt,
        )
