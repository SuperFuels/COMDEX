from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List


class PilotDocumentPdfMissionError(Exception):
    pass


def canonical_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


FORBIDDEN_LIVE_ACTIONS = {
    "payment_submit",
    "domain_purchase",
    "production_deploy",
    "public_post",
    "external_send",
    "booking_create",
    "escrow_create",
    "live_reputation_mutation",
    "memory_mutation",
    "raw_tool_call",
}


@dataclass(frozen=True)
class DocumentPdfMissionRequest:
    business_id: str
    mission_id: str
    mission_run_id: str
    user_request: str
    artifact_title: str
    artifact_format: str = "pdf"
    step_id: str = "step_document_pdf_001"


class PilotDocumentPdfMissionDemo:
    VALID_FORMATS = {"pdf", "document"}

    @classmethod
    def create_demo_plan(cls, req: DocumentPdfMissionRequest) -> Dict[str, Any]:
        if req.artifact_format not in cls.VALID_FORMATS:
            raise PilotDocumentPdfMissionError("unsupported artifact format")

        plan = {
            "schema_version": "aion.pilot.document_pdf_mission_plan.v1",
            "business_id": req.business_id,
            "mission_id": req.mission_id,
            "mission_run_id": req.mission_run_id,
            "user_request": req.user_request,
            "plan_state": "draft_plan_requires_review",
            "live_side_effects_allowed": False,
            "steps": [
                {
                    "step_id": "step_plan_001",
                    "title": "Understand document request",
                    "lane": "autonomous",
                    "output": "structured_document_brief",
                },
                {
                    "step_id": "step_plan_002",
                    "title": "Create draft document content",
                    "lane": "autonomous",
                    "output": "draft_document_body",
                },
                {
                    "step_id": req.step_id,
                    "title": "Generate draft PDF/document artifact",
                    "lane": "autonomous",
                    "output": "draft_artifact_preview",
                },
                {
                    "step_id": "step_plan_004",
                    "title": "Emit receipt, proof and replay",
                    "lane": "autonomous",
                    "output": "artifact_receipt_and_replay",
                },
            ],
            "blocked_live_actions": sorted(FORBIDDEN_LIVE_ACTIONS),
        }
        plan["plan_hash"] = canonical_hash(plan)
        return plan

    @classmethod
    def build_draft_artifact(cls, req: DocumentPdfMissionRequest, plan: Dict[str, Any]) -> Dict[str, Any]:
        if plan.get("live_side_effects_allowed") is not False:
            raise PilotDocumentPdfMissionError("document mission must be draft/preview only")

        artifact_name = f"{req.artifact_title.lower().replace(' ', '_')}.{req.artifact_format}"
        container_path = (
            f"business/{req.business_id}/missions/{req.mission_id}/"
            f"runs/{req.mission_run_id}/artifacts/{artifact_name}"
        )

        if ".." in container_path.split("/"):
            raise PilotDocumentPdfMissionError("artifact path must not contain parent traversal")

        artifact = {
            "schema_version": "aion.pilot.document_pdf_artifact.v1",
            "artifact_type": req.artifact_format,
            "artifact_title": req.artifact_title,
            "artifact_name": artifact_name,
            "business_id": req.business_id,
            "mission_id": req.mission_id,
            "mission_run_id": req.mission_run_id,
            "step_id": req.step_id,
            "business_container_path": container_path,
            "status": "draft_preview",
            "content_summary": {
                "source_request": req.user_request,
                "sections": [
                    "Title",
                    "Purpose",
                    "Input Data",
                    "Generated Summary",
                    "Next Actions",
                    "Proof Metadata",
                ],
            },
            "live_side_effects_allowed": False,
        }
        artifact["artifact_hash"] = canonical_hash(artifact)
        return artifact

    @classmethod
    def create_artifact_receipt(
        cls,
        req: DocumentPdfMissionRequest,
        plan: Dict[str, Any],
        artifact: Dict[str, Any],
    ) -> Dict[str, Any]:
        receipt = {
            "schema_version": "aion.pilot.document_pdf_artifact_receipt.v1",
            "business_id": req.business_id,
            "mission_id": req.mission_id,
            "mission_run_id": req.mission_run_id,
            "step_id": req.step_id,
            "plan_hash": plan["plan_hash"],
            "artifact_hash": artifact["artifact_hash"],
            "artifact_path": artifact["business_container_path"],
            "receipt_state": "sealed_draft_artifact_receipt",
            "external_side_effects": {
                "payment_created": False,
                "booking_created": False,
                "escrow_created": False,
                "external_message_sent": False,
                "production_deployed": False,
                "public_post_created": False,
                "live_reputation_mutated": False,
            },
        }
        receipt["receipt_hash"] = canonical_hash(receipt)
        return receipt

    @classmethod
    def create_replay_proof(
        cls,
        req: DocumentPdfMissionRequest,
        plan: Dict[str, Any],
        artifact: Dict[str, Any],
        receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        replay = {
            "schema_version": "aion.pilot.document_pdf_replay.v1",
            "business_id": req.business_id,
            "mission_id": req.mission_id,
            "mission_run_id": req.mission_run_id,
            "events": [
                {
                    "event_type": "mission_request_received",
                    "visible_to_user": True,
                    "hash": canonical_hash({"request": req.user_request}),
                },
                {
                    "event_type": "deterministic_plan_created",
                    "visible_to_user": True,
                    "hash": plan["plan_hash"],
                },
                {
                    "event_type": "draft_artifact_prepared",
                    "visible_to_user": True,
                    "hash": artifact["artifact_hash"],
                },
                {
                    "event_type": "artifact_receipt_emitted",
                    "visible_to_user": True,
                    "hash": receipt["receipt_hash"],
                },
            ],
            "replay_state": "non_executing_read_model",
            "may_execute_tools": False,
            "may_mutate_provider_state": False,
        }
        replay["replay_hash"] = canonical_hash(replay)

        proof = {
            "schema_version": "aion.pilot.document_pdf_proof.v1",
            "business_id": req.business_id,
            "mission_id": req.mission_id,
            "mission_run_id": req.mission_run_id,
            "plan_hash": plan["plan_hash"],
            "artifact_hash": artifact["artifact_hash"],
            "receipt_hash": receipt["receipt_hash"],
            "replay_hash": replay["replay_hash"],
            "proof_state": "sealed_preview_proof",
            "draft_preview_only": True,
            "live_side_effects_allowed": False,
        }
        proof["proof_hash"] = canonical_hash(proof)
        return {"replay": replay, "proof": proof}

    @classmethod
    def run_demo(cls, req: DocumentPdfMissionRequest) -> Dict[str, Any]:
        plan = cls.create_demo_plan(req)
        artifact = cls.build_draft_artifact(req, plan)
        receipt = cls.create_artifact_receipt(req, plan, artifact)
        proof_bundle = cls.create_replay_proof(req, plan, artifact, receipt)

        cockpit_view = {
            "schema_version": "aion.pilot.document_pdf_cockpit_view.v1",
            "status": "completed_draft_preview",
            "visible_message": "AION prepared the draft document and saved it inside the business container.",
            "safety_message": "AION stopped itself before doing anything risky.",
            "plan": plan,
            "artifact": artifact,
            "receipt": receipt,
            "replay": proof_bundle["replay"],
            "proof": proof_bundle["proof"],
            "open_output_enabled": True,
            "download_output_enabled": True,
            "view_receipt_enabled": True,
            "live_action_buttons_visible": False,
        }
        cockpit_view["cockpit_view_hash"] = canonical_hash(cockpit_view)
        return cockpit_view
