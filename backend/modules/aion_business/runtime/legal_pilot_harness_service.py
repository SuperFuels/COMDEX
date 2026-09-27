"""Evidence-bound Legal Pilot harness with no autonomous external authority."""

from __future__ import annotations

import re
from typing import Any, Sequence

from backend.modules.aion_business.runtime.legal_document_service import LegalDocumentError, LegalDocumentService
from backend.modules.aion_business.runtime.legal_matter_service import LegalMatterService


class LegalPilotHarnessService:
    SCHEMA_VERSION = "tessaris.legal-pilot-harness.v1"

    def __init__(
        self, document_service: LegalDocumentService | None = None,
        matter_service: LegalMatterService | None = None,
    ) -> None:
        self.documents = document_service or LegalDocumentService()
        self.matters = matter_service or LegalMatterService()

    def handle(
        self, workspace_id: str, question: str, *, actor_id: str,
        attachments: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        instruction = " ".join(str(question or "").split()).strip()[:2000]
        if not instruction:
            raise ValueError("legal_pilot_instruction_required")
        attachment_ids = [str(item).strip() for item in list(attachments or [])]
        if len(attachment_ids) > 3:
            raise ValueError("legal_pilot_attachment_limit_exceeded")
        if any(not re.fullmatch(r"document-[a-f0-9]{32}", item) for item in attachment_ids):
            raise ValueError("legal_pilot_requires_protected_document_ids")
        records = [self.documents.get_document(workspace_id, item, include_text=True) for item in attachment_ids]
        lowered = instruction.casefold()
        evidence = [{"source": f"legal_document.{item['document_id']}", "sha256": item["content_sha256"]} for item in records]
        receipts: list[dict[str, Any]] = []

        if len(records) >= 2 and any(term in lowered for term in ("compare", "difference", "changed", "version")):
            comparison = self.documents.compare_versions(
                workspace_id, records[0]["document_id"], records[1]["document_id"], actor_id=actor_id,
            )
            receipts.append({"capability": "legal.compare_versions", "comparison_id": comparison["comparison_id"]})
            content = (
                f"I compared {records[0]['filename']} with {records[1]['filename']} using their exact stored versions. "
                f"I found {comparison['added_line_count']} added and {comparison['removed_line_count']} removed line(s). "
                "Open the document review panel for the exact diff. A person must assess legal effect; nothing was sent or changed."
            )
        elif records:
            summaries = []
            for document in records:
                review = self.documents.review_contract(workspace_id, document["document_id"], actor_id=actor_id)
                receipts.append({"capability": "legal.review_contract", "review_id": review["review_id"],
                                 "document_id": document["document_id"]})
                high = [item["title"] for item in review["findings"] if item["severity"] == "HIGH"]
                review_items = [item["title"] for item in review["findings"] if item["severity"] != "HIGH"]
                summaries.append(
                    f"{document['filename']}: {review['finding_count']} review signal(s)"
                    + (f"; high-attention: {', '.join(high)}" if high else "")
                    + (f"; also check: {', '.join(review_items[:5])}" if review_items else "")
                )
            content = "Local evidence-bound review completed. " + " ".join(summaries) + (
                " These are explainable triage signals, not legal conclusions. Confirm the jurisdiction and use qualified legal advice for material decisions. "
                "No original was changed and nothing was sent externally."
            )
        else:
            matters = self.matters.list_matters(workspace_id)
            documents = self.documents.list_documents(workspace_id)
            open_matters = [item for item in matters if item.get("status") != "CLOSED"]
            urgent = [item for item in open_matters if item.get("risk") in {"HIGH", "URGENT"}]
            content = (
                f"The protected Legal workspace has {len(open_matters)} open matter(s), {len(urgent)} high-priority matter(s) "
                f"and {len(documents)} encrypted document(s). Attach a protected document to run local clause and risk triage, "
                "or open the Legal workspace to compare versions, prepare a controlled redline, record an obligation or draft a human-professional escalation. "
                "I cannot represent the business, make a legal determination or send anything externally."
            )
            evidence = [
                {"source": f"legal_matter.{item['matter_id']}", "status": item["status"], "risk": item["risk"]}
                for item in open_matters[:12]
            ]

        return {
            "schema_version": self.SCHEMA_VERSION,
            "handled": True,
            "content": content,
            "evidence": evidence,
            "action_receipts": receipts,
            "reliability": "deterministic_local_legal_harness",
            "human_review_required": True,
            "not_legal_advice": True,
            "external_writes_performed": False,
            "external_delivery_authorized": False,
            "approval_gated": True,
        }
