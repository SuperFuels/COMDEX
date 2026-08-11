"""Canonical daily receipt and invoice intake for Finance.

Every capture channel terminates in the same immutable-source/document-state
contract.  This module deliberately prepares accounting work but never writes
to Xero or another provider.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.business_containers import (
    BusinessContainerMeta,
    FinanceInboxContainer,
)
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_expense_policy import (
    assess_expense,
    default_expense_policy,
    learned_mapping,
)
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".pdf", ".csv", ".xml"}
DOCUMENT_TYPES = {"receipt", "supplier_invoice", "sales_invoice", "credit_note", "expense_claim", "other"}
DECISIONS = {"approve", "reject", "needs_information"}


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()


def _safe_filename(value: str) -> str:
    name = Path(str(value or "document")).name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return cleaned[:180] or "document"


def intake_channels() -> list[dict[str, Any]]:
    return [
        {"id": "desktop_upload", "name": "Upload from this device", "status": "enabled", "transport": "multipart_upload"},
        {"id": "mobile_photo", "name": "Phone photo / mobile app", "status": "planned", "transport": "same_inbox_contract"},
        {"id": "agent_mailbox", "name": "Finance Agent mailbox", "status": "planned", "transport": "email_adapter"},
        {"id": "forwarded_email", "name": "Forwarded receipt or invoice email", "status": "planned", "transport": "email_adapter"},
        {"id": "mobile_share", "name": "Phone share sheet", "status": "planned", "transport": "authenticated_upload_link"},
        {"id": "scanner", "name": "Scanner / watched folder", "status": "planned", "transport": "file_adapter"},
        {"id": "accounting_connector", "name": "Accounting provider", "status": "planned", "transport": "provider_adapter"},
        {"id": "api", "name": "External API", "status": "planned", "transport": "signed_api"},
    ]


class FinanceInboxService:
    def __init__(self, repository: BusinessContainerRepository | None = None, receipt_reader: Any | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = OrganizationAuthorityService(self.repository)
        self.receipt_reader = receipt_reader

    def empty(self, workspace_id: str) -> dict[str, Any]:
        now = _now()
        model = FinanceInboxContainer(
            id=f"finance-inbox-{workspace_id}", workspace_id=workspace_id,
            meta=BusinessContainerMeta(
                workspace_id=workspace_id, container_key="finance_inbox",
                updated_at=now, source="finance_inbox",
            ),
            intake_channels=intake_channels(),
            accounting_destinations=[
                {"id": "expense", "name": "Business expense", "posting_kind": "spend_money"},
                {"id": "supplier_bill", "name": "Supplier bill", "posting_kind": "accounts_payable"},
                {"id": "sales_invoice", "name": "Sales invoice", "posting_kind": "accounts_receivable"},
                {"id": "credit_note", "name": "Credit note", "posting_kind": "credit_adjustment"},
            ],
            expense_policy=default_expense_policy(),
            governance={
                "original_bytes_immutable": True,
                "deduplicate_by_content_hash": True,
                "extraction_is_suggestion": True,
                "human_review_required": True,
                "authority_check_required": True,
                "exact_payload_approval_required": True,
                "external_writes_enabled": False,
                "provider_neutral": True,
            },
            provenance={"created_at": now, "source": "finance_inbox.v1"},
            revision=0,
        ).model_dump(mode="json")
        model["summary"] = self._summary(model)
        return model

    def get(self, workspace_id: str) -> dict[str, Any]:
        model = self.repository.load_optional_dict(workspace_id, "finance_inbox") or self.empty(workspace_id)
        model["summary"] = self._summary(model)
        return model

    def ingest(
        self,
        workspace_id: str,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None,
        channel: str = "desktop_upload",
        document_type: str = "receipt",
        submitted_by_person_id: str | None = None,
        department_id: str | None = None,
        project_id: str | None = None,
        card_asset_id: str | None = None,
        sender_address: str | None = None,
        source_reference: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        if not content:
            raise ValueError("empty_finance_document")
        if len(content) > MAX_DOCUMENT_BYTES:
            raise ValueError("finance_document_too_large")
        safe_name = _safe_filename(filename)
        extension = Path(safe_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(f"unsupported_finance_document_type:{extension or 'none'}")
        if document_type not in DOCUMENT_TYPES:
            raise ValueError("unsupported_finance_document_class")

        digest = sha256(content).hexdigest()
        document_id = f"finance-document-{digest[:24]}"
        model = self.get(workspace_id)
        duplicate = next((item for item in model["documents"] if item.get("source", {}).get("content_hash") == f"sha256:{digest}"), None)
        if duplicate:
            return deepcopy(duplicate), True

        organisation = self.authority.get(workspace_id)
        people = {item["id"]: item for item in organisation.get("people", [])}
        departments = {item["id"]: item for item in organisation.get("departments", [])}
        assets = {item["id"]: item for item in organisation.get("assets", [])}
        submitter = people.get(submitted_by_person_id or "")
        if submitted_by_person_id and not submitter:
            raise ValueError("finance_document_submitter_not_found")
        if department_id and department_id not in departments:
            raise ValueError("finance_document_department_not_found")
        card = assets.get(card_asset_id or "")
        if card_asset_id and (not card or card.get("asset_type") != "company_card"):
            raise ValueError("finance_document_card_not_found")
        if card and submitter and card.get("assigned_person_id") not in {None, submitter["id"]}:
            raise ValueError("finance_document_card_assigned_to_another_person")

        resolved_department = department_id or ((submitter or {}).get("department_ids") or [None])[0]
        resolved_project = project_id or ((submitter or {}).get("project_ids") or [None])[0]
        submission_decision = self.authority.access_decision(
            workspace_id, person_id=submitted_by_person_id or "", capability="expenses.submit",
            department_id=resolved_department,
        ) if submitted_by_person_id else {
            "allowed": False, "reason": "authenticated_submitter_required",
            "decision_source": "organization_authority.v1",
        }

        root = AIONBusinessPaths.business_container_dir(workspace_id) / "finance" / "inbox" / "documents" / document_id
        root.mkdir(parents=True, exist_ok=True)
        stored_name = f"original{extension}"
        destination = (root / stored_name).resolve()
        business_root = AIONBusinessPaths.business_container_dir(workspace_id).resolve()
        try:
            destination.relative_to(business_root)
        except ValueError as exc:
            raise ValueError("finance_document_path_escape") from exc
        destination.write_bytes(content)
        relative_path = str(destination.relative_to(AIONBusinessPaths.ROOT.resolve()))
        preview_kind = "image" if extension in {".jpg", ".jpeg", ".png", ".webp", ".heic"} else "pdf" if extension == ".pdf" else "document"
        now = _now()
        document = {
            "id": document_id,
            "status": "needs_review" if submission_decision.get("allowed") else "needs_submitter",
            "document_type": document_type,
            "source": {
                "channel": channel, "filename": safe_name, "mime_type": mime_type or "application/octet-stream",
                "byte_size": len(content), "content_hash": f"sha256:{digest}", "storage_path": relative_path,
                "preview_kind": preview_kind, "received_at": now,
                "sender_address": str(sender_address or "").strip().lower() or None,
                "source_reference": str(source_reference or "").strip() or None,
            },
            "ownership": {
                "submitted_by_person_id": submitted_by_person_id,
                "department_id": resolved_department,
                "project_id": resolved_project,
                "cost_center": (submitter or {}).get("cost_center") or None,
                "card_asset_id": card_asset_id,
            },
            "extraction": {
                "status": "not_run",
                "method": "not_run",
                "fields": {},
                "confidence": {},
                "warnings": ["The document has not been read yet. Run the reader or enter the accounting facts manually."],
            },
            "allocation": {"account_code": None, "account_name": None, "tax_code": None, "tracking": []},
            "authority": {
                "submission": submission_decision,
                "approval_route": self._approval_route(workspace_id, submitted_by_person_id, resolved_department, None),
            },
            "review": {"status": "not_reviewed", "reviewed_at": None, "reviewed_by_person_id": None},
            "approval": {"status": "not_requested", "decision": None, "decided_at": None, "decided_by_person_id": None},
            "accounting": {
                "destination": self._default_destination(document_type), "provider": "provider_neutral",
                "status": "not_prepared", "exact_payload": None, "payload_hash": None,
                "external_write_performed": False,
            },
            "history": [{"event": "document_received", "at": now, "channel": channel}],
            "created_at": now, "updated_at": now,
        }
        model["documents"].append(document)
        self._save(workspace_id, model, "document_received", {"document_id": document_id, "channel": channel, "content_hash": f"sha256:{digest}"})
        return deepcopy(document), False

    def extract(
        self,
        workspace_id: str,
        document_id: str,
        *,
        provider: str | None = None,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        """Read visible facts and create suggestions; never approve or post."""
        model = self.get(workspace_id)
        self._check_revision(model, expected_revision)
        document = self._document(model, document_id)
        path, _ = self.file_path(workspace_id, document_id)
        reader = self.receipt_reader
        if reader is None:
            from backend.modules.aion_business.runtime.finance_receipt_vision import FinanceReceiptVisionReader

            selected_provider = provider or (model.get("expense_policy") or {}).get("receipt_reader_provider") or "auto"
            reader = FinanceReceiptVisionReader(provider=selected_provider)
        try:
            result = reader.read(path, expected_document_type=document.get("document_type") or "receipt")
        except Exception as exc:
            document["extraction"] = {
                **document.get("extraction", {}), "status": "failed", "method": "vision_reader_failed",
                "warnings": [self._reader_error(exc)], "failed_at": _now(),
            }
            document["updated_at"] = _now()
            document.setdefault("history", []).append({"event": "document_extraction_failed", "at": _now()})
            self._save(workspace_id, model, "document_extraction_failed", {"document_id": document_id, "error": type(exc).__name__})
            raise

        facts = deepcopy(result.get("facts") or {})
        fields = self._normalise_fields(facts)
        warnings = list(facts.get("uncertainties") or [])
        if fields.get("total") is not None and fields.get("net") is not None and fields.get("tax") is not None:
            if abs(float(fields["total"]) - float(fields["net"]) - float(fields["tax"]) - float(facts.get("tip") or 0)) > 0.02:
                warnings.append("Extracted amounts do not reconcile: net plus tax plus tip does not equal total.")
        missing = [key for key in ("supplier", "document_date", "total") if fields.get(key) in (None, "")]
        if missing:
            warnings.append("Reader could not establish: " + ", ".join(missing) + ".")
        assessment = assess_expense(
            facts, learned_mappings=model.get("learned_mappings", []),
            policy={**default_expense_policy(), **(model.get("expense_policy") or {})},
        )
        suggestion = assessment.get("suggestion") or {}
        for key in ("category", "category_label", "account_code", "account_name", "tax_code"):
            if suggestion.get(key) not in (None, ""):
                document.setdefault("allocation", {})[key] = suggestion[key]
        warnings.extend(self._policy_warning(item) for item in assessment.get("review_flags", []))
        document["extraction"] = {
            "status": "suggestions_ready" if not missing else "needs_information",
            "method": "provider_neutral_structured_vision.v1",
            "fields": fields,
            "line_items": facts.get("line_items") or [],
            "confidence": facts.get("field_confidence") or {},
            "warnings": list(dict.fromkeys(item for item in warnings if item)),
            "expense_assessment": assessment,
            "reader": {key: result.get(key) for key in ("provider", "model", "response_id", "latency_ms", "usage", "source_sent_externally", "provider_storage_requested")},
            "extracted_at": _now(),
        }
        document["status"] = "needs_review" if document.get("status") != "needs_submitter" else "needs_submitter"
        document["updated_at"] = _now()
        document.setdefault("history", []).append({
            "event": "document_suggestions_created", "at": _now(),
            "method": "provider_neutral_structured_vision.v1", "provider": result.get("provider"),
        })
        self._save(workspace_id, model, "document_suggestions_created", {
            "document_id": document_id, "reader": result.get("provider"), "model": result.get("model"),
            "straight_through_candidate": assessment.get("straight_through_candidate", False),
        })
        return deepcopy(document)

    def update_expense_policy(
        self, workspace_id: str, policy: dict[str, Any], *, expected_revision: int | None = None,
    ) -> dict[str, Any]:
        model = self.get(workspace_id)
        self._check_revision(model, expected_revision)
        allowed = set(default_expense_policy())
        clean = {key: value for key, value in policy.items() if key in allowed}
        if "receipt_reader_provider" in clean:
            selected = str(clean["receipt_reader_provider"] or "auto").strip().lower()
            aliases = {"anthropic": "claude", "xai": "grok", "moonshot": "kimi", "ollama": "gemma", "local_gemma": "gemma", "llama": "meta", "meta_ai": "meta", "mistralai": "mistral", "deep_seek": "deepseek"}
            selected = aliases.get(selected, selected)
            if selected not in {"auto", "openai", "gemini", "claude", "grok", "kimi", "gemma", "meta", "mistral", "deepseek"}:
                raise ValueError("finance_receipt_reader_provider_invalid")
            clean["receipt_reader_provider"] = selected
        for key in ("meal_daily_allowance", "meal_receipt_limit", "mileage_rate"):
            if key in clean:
                clean[key] = self._number(clean[key])
                if clean[key] is not None and clean[key] < 0:
                    raise ValueError("finance_expense_policy_amount_invalid")
        model["expense_policy"] = {**default_expense_policy(), **(model.get("expense_policy") or {}), **clean}
        self._save(workspace_id, model, "expense_policy_updated", {"changed_fields": sorted(clean)})
        return deepcopy(model["expense_policy"])

    def review(
        self,
        workspace_id: str,
        document_id: str,
        *,
        fields: dict[str, Any],
        ownership: dict[str, Any] | None = None,
        allocation: dict[str, Any] | None = None,
        destination: str | None = None,
        reviewed_by_person_id: str | None = None,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        model = self.get(workspace_id)
        self._check_revision(model, expected_revision)
        document = self._document(model, document_id)
        organisation = self.authority.get(workspace_id)
        people = {item["id"]: item for item in organisation.get("people", [])}
        departments = {item["id"]: item for item in organisation.get("departments", [])}
        assets = {item["id"]: item for item in organisation.get("assets", [])}

        new_ownership = {**document.get("ownership", {}), **(ownership or {})}
        person_id = new_ownership.get("submitted_by_person_id")
        if person_id not in people:
            raise ValueError("finance_document_submitter_required")
        if new_ownership.get("department_id") and new_ownership["department_id"] not in departments:
            raise ValueError("finance_document_department_not_found")
        card_id = new_ownership.get("card_asset_id")
        card = assets.get(card_id) if card_id else None
        if card_id and (not card or card.get("asset_type") != "company_card"):
            raise ValueError("finance_document_card_not_found")
        if card and card.get("assigned_person_id") not in {None, person_id}:
            raise ValueError("finance_document_card_assigned_to_another_person")

        normalised_fields = self._normalise_fields(fields)
        missing = [key for key in ("supplier", "document_date", "total") if normalised_fields.get(key) in (None, "")]
        business_context = (allocation or {}).get("business_context") or document.get("allocation", {}).get("business_context") or {}
        questions = document.get("extraction", {}).get("expense_assessment", {}).get("questions", [])
        missing_context = [item.get("id") for item in questions if item.get("id") and not str(business_context.get(item["id"]) or "").strip()]
        warnings: list[str] = []
        total, net, tax = (normalised_fields.get(key) for key in ("total", "net", "tax"))
        if total is not None and net is not None and tax is not None and abs(total - net - tax) > 0.02:
            warnings.append("Net plus tax does not equal the total.")
        if card and total is not None and card.get("transaction_limit") is not None and total > float(card["transaction_limit"]):
            warnings.append("The amount exceeds the assigned card transaction limit.")
        if missing_context:
            missing.extend("business_context." + item for item in missing_context)
            warnings.append("Business context is required before this exception can be routed for approval.")

        document["ownership"] = new_ownership
        document["extraction"] = {
            **document.get("extraction", {}),
            "status": "human_confirmed" if not missing else "needs_information",
            "method": "human_review", "fields": normalised_fields,
            "confidence": {key: 1.0 for key, value in normalised_fields.items() if value not in (None, "")},
            "warnings": warnings + (["Required fields are missing: " + ", ".join(missing)] if missing else []),
        }
        document["allocation"] = {**document.get("allocation", {}), **(allocation or {})}
        mapping = learned_mapping(normalised_fields.get("supplier"), document["allocation"])
        if mapping:
            mappings = [item for item in model.get("learned_mappings", []) if item.get("supplier_key") != mapping["supplier_key"]]
            mapping["confirmed_at"] = _now()
            mapping["confirmed_by_person_id"] = reviewed_by_person_id
            model["learned_mappings"] = mappings + [mapping]
        if destination:
            if destination not in {item["id"] for item in model.get("accounting_destinations", [])}:
                raise ValueError("finance_accounting_destination_invalid")
            document["accounting"]["destination"] = destination
        amount = normalised_fields.get("total")
        document["authority"]["submission"] = self.authority.access_decision(
            workspace_id, person_id=person_id, capability="expenses.submit",
            department_id=new_ownership.get("department_id"),
        )
        document["authority"]["approval_route"] = self._approval_route(
            workspace_id, person_id, new_ownership.get("department_id"), amount,
        )
        document["review"] = {
            "status": "confirmed" if not missing else "needs_information",
            "reviewed_at": _now(), "reviewed_by_person_id": reviewed_by_person_id,
        }
        document["approval"] = {
            **document.get("approval", {}),
            "status": "awaiting_approval" if not missing else "not_requested",
        }
        document["status"] = "awaiting_approval" if not missing else "needs_information"
        document["updated_at"] = _now()
        document.setdefault("history", []).append({"event": "document_reviewed", "at": _now(), "by": reviewed_by_person_id})
        self._save(workspace_id, model, "document_reviewed", {"document_id": document_id, "status": document["status"]})
        return deepcopy(document)

    def decide(
        self,
        workspace_id: str,
        document_id: str,
        *,
        decision: str,
        decided_by_person_id: str,
        note: str | None = None,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        if decision not in DECISIONS:
            raise ValueError("finance_document_decision_invalid")
        model = self.get(workspace_id)
        self._check_revision(model, expected_revision)
        document = self._document(model, document_id)
        if document.get("status") not in {"awaiting_approval", "needs_information"}:
            raise ValueError("finance_document_not_ready_for_decision")
        amount = document.get("extraction", {}).get("fields", {}).get("total")
        authority = self.authority.access_decision(
            workspace_id, person_id=decided_by_person_id, capability="expenses.approve",
            department_id=document.get("ownership", {}).get("department_id"), amount=amount,
        )
        if decision == "approve" and not authority.get("allowed"):
            raise PermissionError(authority.get("reason") or "finance_document_approval_not_authorised")

        now = _now()
        document["approval"] = {
            "status": "approved" if decision == "approve" else decision,
            "decision": decision, "decided_at": now,
            "decided_by_person_id": decided_by_person_id, "note": str(note or "").strip() or None,
            "authority_decision": authority,
        }
        if decision == "approve":
            exact_payload = self._accounting_payload(workspace_id, document)
            document["accounting"].update({
                "status": "approved_draft_ready_for_provider_adapter",
                "exact_payload": exact_payload, "payload_hash": _hash(exact_payload),
                "external_write_performed": False,
            })
            document["status"] = "approved_for_accounting"
        elif decision == "reject":
            document["status"] = "rejected"
        else:
            document["status"] = "needs_information"
        document["updated_at"] = now
        document.setdefault("history", []).append({"event": f"document_{decision}", "at": now, "by": decided_by_person_id})
        self._save(workspace_id, model, "document_decision", {"document_id": document_id, "decision": decision, "by": decided_by_person_id})
        return deepcopy(document)

    def file_path(self, workspace_id: str, document_id: str) -> tuple[Path, dict[str, Any]]:
        document = self._document(self.get(workspace_id), document_id)
        relative = str(document.get("source", {}).get("storage_path") or "")
        path = (AIONBusinessPaths.ROOT / relative).resolve()
        root = AIONBusinessPaths.business_container_dir(workspace_id).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("finance_document_path_escape") from exc
        if not path.exists():
            raise FileNotFoundError("finance_document_bytes_missing")
        return path, document

    @staticmethod
    def _document(model: dict[str, Any], document_id: str) -> dict[str, Any]:
        document = next((item for item in model.get("documents", []) if item.get("id") == document_id), None)
        if not document:
            raise KeyError("finance_document_not_found")
        return document

    @staticmethod
    def _check_revision(model: dict[str, Any], expected_revision: int | None) -> None:
        if expected_revision is not None and int(model.get("revision") or 0) != int(expected_revision):
            raise ValueError("finance_inbox_revision_conflict")

    @staticmethod
    def _normalise_fields(fields: dict[str, Any]) -> dict[str, Any]:
        result = {
            "supplier": str(fields.get("supplier") or "").strip() or None,
            "document_date": str(fields.get("document_date") or "").strip() or None,
            "currency": str(fields.get("currency") or "EUR").strip().upper(),
            "total": FinanceInboxService._number(fields.get("total")),
            "net": FinanceInboxService._number(fields.get("net")),
            "tax": FinanceInboxService._number(fields.get("tax")),
            "tip": FinanceInboxService._number(fields.get("tip")),
            "invoice_number": str(fields.get("invoice_number") or "").strip() or None,
            "due_date": str(fields.get("due_date") or "").strip() or None,
            "description": str(fields.get("description") or "").strip() or None,
            "payment_method": str(fields.get("payment_method") or "").strip() or None,
            "card_last_four": str(fields.get("card_last_four") or "").strip()[-4:] or None,
            "merchant_tax_id": str(fields.get("merchant_tax_id") or "").strip() or None,
            "merchant_address": str(fields.get("merchant_address") or "").strip() or None,
        }
        return result

    @staticmethod
    def _number(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return round(float(str(value).replace(",", "").replace("€", "").replace("£", "").strip()), 2)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _reader_error(error: Exception) -> str:
        code = str(error)
        return {
            "receipt_vision_provider_not_configured": "Receipt reader is not configured. Add the vision provider key, then try again.",
            "finance_document_not_supported_by_reader": "This file type cannot be read automatically yet. Review it manually.",
        }.get(code, "The document reader could not produce reliable suggestions. The original is safe; review it manually or try again.")

    @staticmethod
    def _policy_warning(flag: str) -> str:
        labels = {
            "meal_business_context_not_visible_on_receipt": "Meal receipt: confirm the business purpose and attendees.",
            "alcohol_requires_review": "Alcohol is visible: a reviewer must confirm the business treatment.",
            "fuel_business_use_not_visible_on_receipt": "Fuel receipt: confirm the vehicle, journey and reclaim basis.",
            "mixed_purchase_requires_split": "Possible mixed purchase: identify and exclude personal line items.",
            "possible_personal_purchase": "Possible personal purchase: do not treat it as business without confirmation.",
            "meal_exceeds_business_policy_limit": "This meal exceeds the business-configured receipt limit.",
            "business_policy_limit_invalid": "The configured business expense limit is invalid.",
        }
        if flag.startswith("low_confidence_key_fields:"):
            return "Check low-confidence fields: " + flag.split(":", 1)[1].replace(",", ", ") + "."
        return labels.get(flag, flag.replace("_", " ").capitalize() + ".")

    @staticmethod
    def _default_destination(document_type: str) -> str:
        return {
            "receipt": "expense", "expense_claim": "expense", "supplier_invoice": "supplier_bill",
            "sales_invoice": "sales_invoice", "credit_note": "credit_note", "other": "expense",
        }[document_type]

    def _approval_route(self, workspace_id: str, submitter_id: str | None, department_id: str | None, amount: float | None) -> dict[str, Any]:
        organisation = self.authority.get(workspace_id)
        people = {item["id"]: item for item in organisation.get("people", []) if item.get("status") == "active"}
        submitter = people.get(submitter_id or "")
        ordered: list[str] = []
        if submitter and submitter.get("manager_id") in people:
            ordered.append(submitter["manager_id"])
        ordered.extend(item["id"] for item in people.values() if "role.finance_controller" in set(item.get("role_ids") or []))
        ordered.extend(item["id"] for item in people.values() if "role.owner_director" in set(item.get("role_ids") or []))
        seen: set[str] = set()
        candidates = []
        for person_id in ordered:
            if person_id in seen:
                continue
            seen.add(person_id)
            decision = self.authority.access_decision(
                workspace_id, person_id=person_id, capability="expenses.approve",
                department_id=department_id, amount=amount,
            )
            candidates.append({"person_id": person_id, "person_name": people[person_id].get("name"), **decision})
        eligible = [item for item in candidates if item.get("allowed")]
        return {
            "status": "route_available" if eligible else "no_authorised_approver",
            "recommended_approver_person_id": eligible[0]["person_id"] if eligible else None,
            "candidates": candidates,
            "self_approval_only": bool(eligible and all(item["person_id"] == submitter_id for item in eligible)),
        }

    @staticmethod
    def _accounting_payload(workspace_id: str, document: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "aion.finance.accounting_instruction.v1",
            "workspace_id": workspace_id,
            "source_document_id": document["id"],
            "source_document_hash": document["source"]["content_hash"],
            "destination": document["accounting"]["destination"],
            "document_type": document["document_type"],
            "fields": deepcopy(document["extraction"]["fields"]),
            "ownership": deepcopy(document["ownership"]),
            "allocation": deepcopy(document["allocation"]),
            "approval": {
                "decided_by_person_id": document["approval"].get("decided_by_person_id"),
                "decided_at": document["approval"].get("decided_at"),
            },
            "external_write_permitted": False,
        }

    @staticmethod
    def _summary(model: dict[str, Any]) -> dict[str, Any]:
        documents = model.get("documents", [])
        return {
            "total_documents": len(documents),
            "needs_submitter": sum(item.get("status") == "needs_submitter" for item in documents),
            "needs_review": sum(item.get("status") in {"needs_review", "needs_information"} for item in documents),
            "awaiting_approval": sum(item.get("status") == "awaiting_approval" for item in documents),
            "approved_for_accounting": sum(item.get("status") == "approved_for_accounting" for item in documents),
            "rejected": sum(item.get("status") == "rejected" for item in documents),
            "external_writes": sum(bool(item.get("accounting", {}).get("external_write_performed")) for item in documents),
        }

    def _save(self, workspace_id: str, model: dict[str, Any], event_type: str, event: dict[str, Any]) -> None:
        model["revision"] = int(model.get("revision") or 0) + 1
        model["model_status"] = "active" if model.get("documents") else "empty"
        model["summary"] = self._summary(model)
        model.setdefault("meta", {})["updated_at"] = _now()
        model.setdefault("provenance", {})["updated_at"] = _now()
        validated = FinanceInboxContainer(**model)
        self.repository.save_model(validated)
        self._project(workspace_id, validated.model_dump(mode="json"))
        self._audit(workspace_id, event_type, event)

    def _project(self, workspace_id: str, model: dict[str, Any]) -> None:
        summary = deepcopy(model["summary"])
        summary["revision"] = model["revision"]
        summary["status"] = model["model_status"]
        intelligence = self.repository.load_optional_dict(workspace_id, "department_intelligence")
        if intelligence:
            finance = intelligence.setdefault("departments", {}).setdefault("finance", {})
            finance["finance_inbox"] = summary
            finance["boardroom_summary"] = (
                f"Finance Inbox: {summary['needs_review']} need review, "
                f"{summary['awaiting_approval']} await approval and "
                f"{summary['approved_for_accounting']} are approved accounting drafts."
            )
            intelligence["revision"] = int(intelligence.get("revision") or 0) + 1
            intelligence.setdefault("meta", {})["updated_at"] = _now()
            self.repository.save_dict(workspace_id, "department_intelligence", intelligence)
        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom:
            boardroom.setdefault("boardroom", {}).setdefault("runtime", {})["finance_inbox"] = summary
            boardroom.setdefault("meta", {})["updated_at"] = _now()
            self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)

    @staticmethod
    def _audit(workspace_id: str, event_type: str, payload: dict[str, Any]) -> None:
        record = {"event_type": event_type, "occurred_at": _now(), **payload}
        record["event_hash"] = _hash(record)
        path = AIONBusinessPaths.audit_file(workspace_id, "finance_inbox")
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
