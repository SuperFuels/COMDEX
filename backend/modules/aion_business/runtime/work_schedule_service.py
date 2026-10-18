"""Canonical work, booking and field-delivery record shared by every client."""

from __future__ import annotations

import base64
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import secrets
import sys
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.department_operational_store import (
    DepartmentOperationalStore,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore


FINAL_STATUSES = {"cancelled", "completed", "invoiced", "paid"}
ALLOWED_STATUSES = {
    "new", "quote_required", "awaiting_approval", "awaiting_payment", "scheduled", "on_way", "en_route",
    "in_progress", "paused", "completed", "invoiced", "paid", "cancelled",
}


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _clean(value: Any, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[:limit]


def _safe_name(value: Any, fallback: str = "file") -> str:
    name = Path(str(value or fallback)).name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "-", name).strip(" .-")
    return (name or fallback)[:140]


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _money(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        return str(Decimal(str(value).replace("£", "").replace(",", ".")).quantize(Decimal("0.01")))
    except InvalidOperation as error:
        raise ValueError("invalid_money_amount") from error


class WorkScheduleService:
    """Owns one durable schedule model and its evidence files.

    The JSON model is intentionally client-neutral. Desktop and mobile receive
    the same jobs and revision instead of maintaining independent replicas.
    """

    schema_version = "aion.work-schedule.v3"

    def __init__(
        self,
        repository: BusinessContainerRepository | None = None,
        *,
        domain_store: VaultDomainStore | None = None,
        object_store: VaultObjectStore | None = None,
    ) -> None:
        self.domain_store = domain_store
        self.object_store = object_store
        self.repository = repository
        if repository is None and domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(runtime.guardian, actor_id="work-schedule-runtime")
            self.object_store = runtime.objects
        elif repository is None and domain_store is None:
            self.repository = BusinessContainerRepository()
        self.operational_store = (
            DepartmentOperationalStore(domain_store=self.domain_store)
            if self.domain_store is not None
            else None
        )

    @property
    def guardian_backed(self) -> bool:
        return self.domain_store is not None

    def _dir(self, workspace_id: str) -> Path:
        if self.repository is None:
            raise RuntimeError("legacy_work_schedule_path_unavailable_in_guardian_mode")
        path = Path(self.repository.base_dir) / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(self, workspace_id: str) -> Path:
        return self._dir(workspace_id) / "work_schedule.json"

    def _files_dir(self, workspace_id: str, item_id: str) -> Path:
        path = self._dir(workspace_id) / "work_schedule_files" / _safe_name(item_id, "work")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def empty(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "revision": 0, "updated_at": "",
            "items": [], "jobs": [], "intake": [], "resources": [], "customers": [],
            "reminders": [], "stock_movements": [], "portal_access": [],
            "mobile_operation_receipts": [],
            "document_counters": {"quote": 0, "invoice": 0},
        }

    def get(self, workspace_id: str) -> dict[str, Any]:
        if self.domain_store is not None:
            record = self.domain_store.get_optional(
                "work_schedule.records", workspace_id=workspace_id, entity_id="schedule"
            )
            if record is None:
                return self.empty()
            raw = record["payload"]
        else:
            path = self._path(workspace_id)
            if not path.exists():
                return self.empty()
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, TypeError, ValueError):
                return self.empty()
        if not isinstance(raw, Mapping):
            return self.empty()
        items = raw.get("items") if isinstance(raw.get("items"), list) else raw.get("jobs")
        model = self.empty()
        model.update({key: deepcopy(raw.get(key)) for key in model if key in raw})
        model["schema_version"] = self.schema_version
        model["items"] = [self._normalise_item(item) for item in (items or []) if isinstance(item, Mapping)]
        model["customers"] = self._customer_history(
            model["items"],
            [dict(row) for row in (model.get("customers") or []) if isinstance(row, Mapping)],
        )
        model["jobs"] = [self._mobile_job(item) for item in model["items"]]
        model["conflicts"] = self.conflicts(model["items"])
        return model

    def save(
        self, workspace_id: str, payload: Mapping[str, Any], *, expected_revision: int | None = None,
        changed_by: str = "current_user",
    ) -> dict[str, Any]:
        current = self.get(workspace_id)
        if expected_revision is not None and int(expected_revision) != int(current.get("revision") or 0):
            raise ValueError("work_schedule_revision_conflict")
        incoming = payload.get("items") if isinstance(payload.get("items"), list) else payload.get("jobs")
        items = [self._normalise_item(item, actor_id=changed_by) for item in (incoming or []) if isinstance(item, Mapping)]
        ids: set[str] = set()
        for item in items:
            if item["id"] in ids:
                raise ValueError("duplicate_work_item_id")
            ids.add(item["id"])
        model = self.empty()
        model.update({
            "revision": int(current.get("revision") or 0) + 1,
            "updated_at": _now(), "items": items,
            "intake": [self._normalise_intake(row) for row in payload.get("intake", []) if isinstance(row, Mapping)][:1000],
            "resources": [self._normalise_resource(row) for row in payload.get("resources", []) if isinstance(row, Mapping)][:500],
            "customers": [dict(row) for row in payload.get("customers", []) if isinstance(row, Mapping)][:5000],
            "reminders": [dict(row) for row in payload.get("reminders", []) if isinstance(row, Mapping)][:5000],
            "stock_movements": [dict(row) for row in payload.get("stock_movements", []) if isinstance(row, Mapping)][:10000],
            "portal_access": [dict(row) for row in payload.get("portal_access", []) if isinstance(row, Mapping)][:5000],
            "mobile_operation_receipts": [
                dict(row) for row in payload.get("mobile_operation_receipts", [])
                if isinstance(row, Mapping)
            ][-5000:],
            "document_counters": dict(payload.get("document_counters") or current.get("document_counters") or {}),
            "changed_by": _clean(changed_by, 120),
        })
        model["customers"] = self._customer_history(items, model["customers"])
        model["jobs"] = [self._mobile_job(item) for item in items]
        self._write(workspace_id, model)
        self._append_schedule_audit(
            workspace_id,
            before_items=current.get("items") or [],
            after_items=items,
            before_stock_movements=current.get("stock_movements") or [],
            after_stock_movements=model.get("stock_movements") or [],
            revision=model["revision"],
            actor_id=changed_by,
        )
        model["conflicts"] = self.conflicts(items)
        return model

    def action(
        self, workspace_id: str, operation: str, fields: Mapping[str, Any], *, actor_id: str,
        idempotency_key: str = "",
    ) -> dict[str, Any]:
        current = self.get(workspace_id)
        payload = deepcopy(current)
        items = payload["items"]
        operation = str(operation or "").strip().casefold()
        request_hash = self._mobile_request_hash({"operation": operation, "fields": dict(fields)})
        replay = self._mobile_operation_replay(current, idempotency_key, request_hash)
        if replay is not None:
            return {**current, "idempotent_replay": True, "operation_receipt": replay}
        if operation == "create":
            item = self._normalise_item({**dict(fields), "id": fields.get("id") or f"work_{uuid4().hex}"}, actor_id=actor_id)
            if not item["title"]:
                raise ValueError("work_title_required")
            items.append(item)
            self._create_recurrences(items, item)
        elif operation == "update":
            item = next((row for row in items if row["id"] == str(fields.get("id") or "")), None)
            if item is None:
                raise LookupError("work_item_not_found")
            merged = {**item, **dict(fields), "id": item["id"]}
            replacement = self._normalise_item(merged, actor_id=actor_id)
            items[items.index(item)] = replacement
        elif operation == "add_update":
            item = self._find(items, fields)
            text = str(fields.get("text") or "").strip()[:8000]
            if not text:
                raise ValueError("work_update_required")
            item["updates"].append({"id": f"update_{uuid4().hex}", "text": text, "at": _now(), "by": actor_id})
        elif operation == "add_time":
            item = self._find(items, fields)
            minutes = max(1, min(int(fields.get("minutes") or 0), 24 * 60))
            item["time_entries"].append({"id": f"time_{uuid4().hex}", "minutes": minutes, "note": _clean(fields.get("note"), 500), "at": _now(), "by": actor_id})
        elif operation == "checklist":
            item = self._find(items, fields)
            checklist_id = str(fields.get("checklist_id") or "")
            row = next((value for value in item["checklist"] if value["id"] == checklist_id), None)
            if row is None:
                row = {"id": checklist_id or f"check_{uuid4().hex}", "label": _clean(fields.get("label"), 240), "done": False}
                item["checklist"].append(row)
            row["done"] = bool(fields.get("done", True))
            row["updated_at"] = _now()
            row["updated_by"] = actor_id
        elif operation == "add_checklist":
            item = self._find(items, fields)
            label = _clean(fields.get("label"), 240)
            if not label:
                raise ValueError("checklist_label_required")
            item["checklist"].append({"id": f"check_{uuid4().hex}", "label": label, "done": False, "created_at": _now(), "created_by": actor_id})
        elif operation == "add_material":
            item = self._find(items, fields)
            name = _clean(fields.get("name"), 240)
            if not name:
                raise ValueError("material_name_required")
            quantity = max(0, float(fields.get("quantity") or 0))
            item["materials"].append({
                "id": f"material_{uuid4().hex}", "name": name, "quantity": quantity,
                "unit": _clean(fields.get("unit") or "item", 40), "used": bool(fields.get("used", False)),
                "unit_cost": _money(fields.get("unit_cost")), "created_at": _now(), "created_by": actor_id,
            })
        elif operation == "material_status":
            item = self._find(items, fields)
            material = next((row for row in item["materials"] if row.get("id") == fields.get("material_id")), None)
            if material is None:
                raise LookupError("work_material_not_found")
            material["used"] = bool(fields.get("used", True))
            material["updated_at"] = _now()
        elif operation == "stock_movement":
            name = _clean(fields.get("name"), 240)
            if not name:
                raise ValueError("stock_name_required")
            movement_type = _clean(fields.get("movement_type") or "receive", 40).casefold()
            if movement_type not in {"receive", "allocate", "use", "return", "adjust"}:
                raise ValueError("invalid_stock_movement_type")
            quantity = float(fields.get("quantity") or 0)
            if quantity <= 0:
                raise ValueError("stock_quantity_required")
            signed = quantity if movement_type in {"receive", "return"} else -quantity
            payload["stock_movements"].append({
                "id": f"stock_{uuid4().hex}", "name": name, "quantity": signed,
                "movement_type": movement_type, "unit": _clean(fields.get("unit") or "item", 40),
                "item_id": _clean(fields.get("id"), 160), "note": _clean(fields.get("note"), 500),
                "at": _now(), "by": actor_id,
            })
        elif operation == "prepare_reminder":
            item = self._find(items, fields)
            reminder = self._reminder(item, fields, actor_id)
            payload["reminders"].append(reminder)
        else:
            raise ValueError("unsupported_work_schedule_operation")
        receipt = self._append_mobile_operation_receipt(
            payload, idempotency_key=idempotency_key, request_hash=request_hash,
            operation=operation, item_id=str(fields.get("id") or ""), actor_id=actor_id,
        )
        saved = self.save(workspace_id, payload, expected_revision=current["revision"], changed_by=actor_id)
        return {**saved, "idempotent_replay": False, "operation_receipt": receipt} if receipt else saved

    def create_intake(self, workspace_id: str, fields: Mapping[str, Any], *, channel: str = "website") -> dict[str, Any]:
        current = self.get(workspace_id)
        intake = self._normalise_intake({**dict(fields), "channel": channel, "received_at": _now()})
        current["intake"].append(intake)
        # A secured provider intake may already have resolved the canonical CRM
        # contact. Mirror that identity into Work & Schedule so review and
        # conversion reuse the customer rather than manufacturing a duplicate.
        customer_id = _clean(intake.get("customer_id"), 160)
        if customer_id:
            existing = next(
                (row for row in current["customers"] if str(row.get("id") or "") == customer_id),
                None,
            )
            customer = existing if existing is not None else {"id": customer_id, "work_item_ids": []}
            customer.update({
                "name": intake.get("customer") or customer.get("name") or "",
                "email": intake.get("customer_email") or intake.get("email") or customer.get("email") or "",
                "phone": intake.get("customer_phone") or intake.get("phone") or customer.get("phone") or "",
                "billing_address": intake.get("customer_address") or intake.get("address") or customer.get("billing_address") or "",
                "address": intake.get("customer_address") or intake.get("address") or customer.get("address") or "",
                "service_address": intake.get("service_address") or intake.get("location") or customer.get("service_address") or "",
                "source": channel,
                "sales_opportunity_id": intake.get("sales_opportunity_id") or customer.get("sales_opportunity_id") or "",
                "updated_at": _now(),
            })
            if existing is None:
                current["customers"].append(customer)
        return self.save(workspace_id, current, expected_revision=current["revision"], changed_by=f"{channel}_booking")

    def upload(
        self, workspace_id: str, item_id: str, *, filename: str, content_type: str,
        data_base64: str, actor_id: str, idempotency_key: str = "",
    ) -> dict[str, Any]:
        current = self.get(workspace_id)
        item = self._find(current["items"], {"id": item_id})
        try:
            content = base64.b64decode(data_base64, validate=True)
        except Exception as error:
            raise ValueError("invalid_file_encoding") from error
        if not content or len(content) > 20 * 1024 * 1024:
            raise ValueError("file_size_must_be_between_1_byte_and_20mb")
        request_hash = self._mobile_request_hash({
            "operation": "upload_evidence", "item_id": item_id,
            "filename": _safe_name(filename), "content_type": content_type or "application/octet-stream",
            "content_sha256": hashlib.sha256(content).hexdigest(),
        })
        replay = self._mobile_operation_replay(current, idempotency_key, request_hash)
        if replay is not None:
            document = next(
                (row for row in item.get("documents") or [] if row.get("id") == replay.get("document_id")),
                None,
            )
            if document is None:
                raise RuntimeError("mobile_operation_receipt_document_missing")
            return {
                "schedule": {**current, "idempotent_replay": True, "operation_receipt": replay},
                "document": document, "idempotent_replay": True,
            }
        stored_prefix = request_hash[:10] if idempotency_key else uuid4().hex[:10]
        stored_name = f"{stored_prefix}-{_safe_name(filename)}"
        storage = self._store_file_bytes(
            workspace_id, item_id, data=content, filename=_safe_name(filename),
            content_type=content_type or "application/octet-stream", actor_id=actor_id,
            legacy_stored_name=stored_name, idempotency_key=idempotency_key,
        )
        document = {
            "id": f"document_{uuid4().hex}", "name": _safe_name(filename), "stored_name": stored_name,
            "content_type": _clean(content_type or "application/octet-stream", 120), "size": len(content),
            "created_at": _now(), "created_by": actor_id, "kind": "evidence", **storage,
        }
        item["documents"].append(document)
        receipt = self._append_mobile_operation_receipt(
            current, idempotency_key=idempotency_key, request_hash=request_hash,
            operation="upload_evidence", item_id=item_id, actor_id=actor_id,
            document_id=document["id"],
        )
        saved = self.save(workspace_id, current, expected_revision=current["revision"], changed_by=actor_id)
        return {
            "schedule": {**saved, "idempotent_replay": False, "operation_receipt": receipt} if receipt else saved,
            "document": document, "idempotent_replay": False,
        }

    def generate_document(
        self, workspace_id: str, item_id: str, kind: str, *, actor_id: str,
        line_items: list[Mapping[str, Any]] | None = None, tax_rate: Any = "0",
        document_profile: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = self.get(workspace_id)
        item = self._find(current["items"], {"id": item_id})
        kind = kind if kind in {"service_report", "completion_certificate", "quote", "invoice"} else "service_report"
        title = kind.replace("_", " ").title()
        commercial: dict[str, Any] | None = None
        if kind in {"quote", "invoice"}:
            counter = int((current.get("document_counters") or {}).get(kind) or 0) + 1
            current.setdefault("document_counters", {})[kind] = counter
            prefix = "Q" if kind == "quote" else "INV"
            number = f"{prefix}-{datetime.now().year}-{counter:04d}"
            rate = Decimal(str(tax_rate or "0").replace(",", "."))
            rows = self._line_items(line_items or [], fallback_title=item["title"], fallback_amount=(item.get(kind) or {}).get("amount"), default_tax=rate)
            subtotal = sum((Decimal(row["quantity"]) * Decimal(row["unit_price"]) for row in rows), Decimal("0"))
            tax = sum((Decimal(row["quantity"]) * Decimal(row["unit_price"]) * Decimal(row.get("tax_rate") or rate) / Decimal("100") for row in rows), Decimal("0")).quantize(Decimal("0.01"))
            total = (subtotal + tax).quantize(Decimal("0.01"))
            line_rates = {Decimal(str(row.get("tax_rate") or rate)) for row in rows}
            display_rate = next(iter(line_rates)) if len(line_rates) == 1 else rate
            profile_payload = dict(document_profile or {})
            reference = str(profile_payload.get("payment_reference") or number).replace("QUOTE-NUMBER", number).replace("{quote_number}", number)
            profile_payload["payment_reference"] = reference
            commercial = {
                "status": "draft", "number": number, "line_items": rows,
                "subtotal": str(subtotal.quantize(Decimal("0.01"))), "tax_rate": str(display_rate),
                "tax": str(tax), "total": str(total), "amount": str(total), "created_at": _now(),
                "document_profile": profile_payload,
                "payment_method": profile_payload.get("payment_method") or "bank_transfer",
                "payment_schedule": [dict(row) for row in profile_payload.get("payment_schedule") or [] if isinstance(row, Mapping)][:24],
            }
            item[kind] = commercial
            title = f"{title} {number}"
        filename = f"{title} - {_safe_name(item['title'], 'work')}.pdf"
        stored_name = f"{uuid4().hex[:10]}-{_safe_name(filename)}"
        lines = [title, f"Work: {item['title']}", f"Customer: {item['customer'] or 'Not recorded'}", f"Date: {item['date'] or 'Not scheduled'} {item['time']}", f"Location: {item['location'] or 'Not recorded'}", f"Assigned to: {item['assignee'] or 'Unassigned'}", f"Status: {item['status'].replace('_', ' ').title()}"]
        if commercial:
            lines.extend(["", *[f"{row['description']}  {row['quantity']} x GBP {row['unit_price']}" for row in commercial["line_items"]], "", f"Subtotal: GBP {commercial['subtotal']}", f"Tax ({commercial['tax_rate']}%): GBP {commercial['tax']}", f"Total: GBP {commercial['total']}"])
        else:
            lines.extend(["", item["notes"] or "No additional notes."])
        content = (
            self._quotation_pdf(
                title, item, commercial, commercial.get("document_profile") or {}, document_kind=kind,
            )
            if kind in {"quote", "invoice"} and commercial
            else self._simple_pdf(lines)
        )
        storage = self._store_file_bytes(
            workspace_id, item_id, data=content, filename=filename,
            content_type="application/pdf", actor_id=actor_id,
            legacy_stored_name=stored_name,
        )
        document = {"id": f"document_{uuid4().hex}", "name": filename, "stored_name": stored_name, "content_type": "application/pdf", "size": len(content), "created_at": _now(), "created_by": actor_id, "kind": kind, **storage}
        item["documents"].append(document)
        item["updates"].append({"id": f"update_{uuid4().hex}", "text": f"{title} generated and attached.", "at": _now(), "by": actor_id})
        saved = self.save(workspace_id, current, expected_revision=current["revision"], changed_by=actor_id)
        return {"schedule": saved, "document": document, "commercial": commercial}

    def refresh_invoice_document(
        self, workspace_id: str, item_id: str, *, actor_id: str,
        document_profile: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Re-render an existing numbered invoice without changing its number."""
        current = self.get(workspace_id)
        item = self._find(current["items"], {"id": item_id})
        invoice = dict(item.get("invoice") or {})
        if not invoice.get("number"):
            raise LookupError("invoice_not_found")
        profile = dict(document_profile or invoice.get("document_profile") or {})
        invoice["document_profile"] = profile
        item["invoice"] = invoice
        document = next(
            (
                row for row in reversed(item.get("documents") or [])
                if isinstance(row, dict) and row.get("kind") == "invoice"
                and str(invoice.get("number")) in str(row.get("name") or "")
            ),
            None,
        )
        if document is None:
            raise LookupError("invoice_document_not_found")
        content = self._quotation_pdf(
            str(invoice.get("number") or "Invoice"), item, invoice, profile, document_kind="invoice",
        )
        storage = self._store_file_bytes(
            workspace_id, item_id, data=content,
            filename=str(document.get("name") or f"{invoice.get('number')}.pdf"),
            content_type="application/pdf", actor_id=actor_id,
            legacy_stored_name=str(document.get("stored_name") or ""),
        )
        document.update(storage)
        document["size"] = len(content)
        document["updated_at"] = _now()
        document["updated_by"] = actor_id
        saved = self.save(workspace_id, current, expected_revision=current["revision"], changed_by=actor_id)
        saved_item = next(row for row in saved["items"] if row.get("id") == item_id)
        saved_document = next(row for row in saved_item.get("documents") or [] if row.get("id") == document.get("id"))
        return {"schedule": saved, "document": saved_document, "commercial": saved_item.get("invoice")}

    def issue_portal_access(self, workspace_id: str, item_id: str, *, actor_id: str, expires_days: int = 30) -> dict[str, Any]:
        current = self.get(workspace_id)
        item = self._find(current["items"], {"id": item_id})
        token = secrets.token_urlsafe(28)
        access = {
            "id": f"portal_{uuid4().hex}", "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "item_id": item_id, "customer": item.get("customer") or "Customer", "created_at": _now(),
            "created_by": actor_id, "expires_at": (datetime.now(UTC) + timedelta(days=max(1, min(expires_days, 365)))).replace(microsecond=0).isoformat(),
            "revoked": False,
        }
        current["portal_access"].append(access)
        saved = self.save(workspace_id, current, expected_revision=current["revision"], changed_by=actor_id)
        return {"schedule": saved, "token": token, "expires_at": access["expires_at"]}

    def portal_view(self, token: str) -> dict[str, Any]:
        workspace_id, current, access = self._portal_record(token)
        item = self._find(current["items"], {"id": access["item_id"]})
        return {"workspace_id": workspace_id, "item": self._public_item(item), "expires_at": access["expires_at"]}

    def portal_action(self, token: str, operation: str, fields: Mapping[str, Any]) -> dict[str, Any]:
        workspace_id, current, access = self._portal_record(token)
        item = self._find(current["items"], {"id": access["item_id"]})
        operation = _clean(operation, 50).casefold()
        if operation not in {"request_reschedule", "request_cancellation", "approve_quote", "decline_quote"}:
            raise ValueError("unsupported_customer_portal_action")
        request = {"id": f"request_{uuid4().hex}", "operation": operation, "status": "needs_review", "created_at": _now(), "note": _clean(fields.get("note"), 1000)}
        create_invoice = False
        newly_accepted = False
        if operation == "request_reschedule":
            request.update({"requested_date": _clean(fields.get("date"), 10), "requested_time": _clean(fields.get("time"), 5)})
        elif operation == "approve_quote":
            newly_accepted = str((item.get("quote") or {}).get("status") or "") != "customer_approved"
            create_invoice = not bool((item.get("invoice") or {}).get("number"))
            item["quote"] = {**item["quote"], "status": "customer_approved", "approved_at": _now(), "accepted_source": "customer_email"}
            # Acceptance is not payment. Keep the work out of the active
            # schedule until a card provider confirms payment or a bank
            # transaction is reconciled.
            item["status"] = "awaiting_payment"
            request["status"] = "accepted"
            quote = item.get("quote") or {}
            profile = quote.get("document_profile") or {}
            # The document profile contains the frozen, calculated schedule that
            # the customer accepted. The editable builder rows may only contain
            # percentages, so they must not override these calculated amounts.
            stages = profile.get("payment_schedule") or quote.get("payment_schedule") or []
            stage = next((row for row in stages if row.get("due_type") == "acceptance"), stages[0] if stages else {})
            if newly_accepted or not item.get("payment_request"):
                item["payment_request"] = {
                    "id": f"payment_request_{uuid4().hex}", "status": "preparing_delivery",
                    "label": _clean(stage.get("label") or "Payment", 160),
                    "amount": _money(stage.get("calculated_amount") or quote.get("total") or quote.get("amount")),
                    "currency": _clean(((profile.get("business") or {}).get("currency") or "EUR"), 8),
                    "method": _clean(quote.get("payment_method") or profile.get("payment_method") or "bank_transfer", 40),
                    "reference": _clean(profile.get("payment_reference") or quote.get("number"), 160),
                    "due": "When the quote is accepted", "prepared_at": _now(), "trigger": "customer_acceptance",
                }
        elif operation == "decline_quote":
            item["quote"] = {**item["quote"], "status": "customer_declined", "declined_at": _now()}
            request["status"] = "accepted"
        item.setdefault("customer_requests", []).append(request)
        item["updates"].append({"id": f"update_{uuid4().hex}", "text": f"Customer portal: {operation.replace('_', ' ')}.", "at": _now(), "by": "customer_portal"})
        saved = self.save(workspace_id, current, expected_revision=current["revision"], changed_by="customer_portal")
        invoice_result = None
        if operation == "approve_quote" and create_invoice:
            accepted_item = self._find(saved["items"], {"id": item["id"]})
            quote = accepted_item.get("quote") or {}
            payment = accepted_item.get("payment_request") or {}
            rate = Decimal(str(quote.get("tax_rate") or "0"))
            gross = Decimal(str(payment.get("amount") or quote.get("total") or quote.get("amount") or "0"))
            divisor = Decimal("1") + (rate / Decimal("100"))
            net = (gross / divisor if divisor else gross).quantize(Decimal("0.01"))
            quote_profile = dict(quote.get("document_profile") or {})
            invoice_result = self.generate_document(
                workspace_id, item["id"], "invoice", actor_id="customer_acceptance",
                line_items=[{"description": payment.get("label") or accepted_item.get("title") or "Payment", "quantity": 1, "unit_price": str(net), "tax_rate": str(rate)}],
                tax_rate=str(rate),
                document_profile={**quote_profile, "payment_reference": payment.get("reference") or quote.get("number"), "source_quote_number": quote.get("number"), "payment_stage": dict(payment)},
            )
            saved = invoice_result["schedule"]
        saved_item = self._find(saved["items"], {"id": item["id"]})
        return {
            "schedule": saved, "workspace_id": workspace_id, "request": request,
            "item": self._public_item(saved_item), "invoice": (invoice_result or {}).get("commercial") or saved_item.get("invoice"),
            "invoice_document": (invoice_result or {}).get("document"),
            "payment_request": saved_item.get("payment_request"), "newly_accepted": newly_accepted,
        }

    def record_payment_delivery(
        self, workspace_id: str, item_id: str, *, status: str, details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = self.get(workspace_id)
        item = self._find(current["items"], {"id": item_id})
        payment = dict(item.get("payment_request") or {})
        delivery_details = dict(details or {})
        update_text = _clean(delivery_details.pop("update_text", "Payment request delivery updated."), 1000)
        payment.update({"status": _clean(status, 80), "delivery_updated_at": _now(), **delivery_details})
        item["payment_request"] = payment
        item["updates"].append({
            "id": f"update_{uuid4().hex}",
            "text": update_text,
            "at": _now(), "by": "automatic_payment_delivery",
        })
        return self.save(workspace_id, current, expected_revision=current["revision"], changed_by="automatic_payment_delivery")

    def prepare_due_reminders(self, workspace_id: str, *, now: datetime | None = None, hours_ahead: int = 48) -> dict[str, Any]:
        current = self.get(workspace_id)
        moment = now or datetime.now(UTC)
        added = False
        existing = {(row.get("item_id"), row.get("kind")) for row in current["reminders"] if row.get("status") not in {"cancelled", "failed"}}
        for item in current["items"]:
            start, _ = self._bounds(item)
            if not start or item.get("status") in FINAL_STATUSES:
                continue
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)
            delta = (start - moment).total_seconds() / 3600
            kind = "appointment_24h" if 2 < delta <= hours_ahead else "appointment_2h" if 0 <= delta <= 2 else ""
            if kind and (item["id"], kind) not in existing:
                current["reminders"].append(self._reminder(item, {"kind": kind}, "work_scheduler"))
                added = True
        return self.save(workspace_id, current, expected_revision=current["revision"], changed_by="work_scheduler") if added else current

    def file_path(self, workspace_id: str, item_id: str, document_id: str) -> tuple[Path, dict[str, Any]]:
        if self.guardian_backed:
            raise RuntimeError("guardian_work_document_has_no_plaintext_path")
        item = self._find(self.get(workspace_id)["items"], {"id": item_id})
        document = next((row for row in item["documents"] if isinstance(row, Mapping) and row.get("id") == document_id), None)
        if document is None:
            raise LookupError("work_document_not_found")
        path = self._files_dir(workspace_id, item_id) / _safe_name(document.get("stored_name"))
        if not path.is_file():
            raise LookupError("work_document_file_not_found")
        return path, dict(document)

    def file_bytes(self, workspace_id: str, item_id: str, document_id: str) -> tuple[bytes, dict[str, Any]]:
        item = self._find(self.get(workspace_id)["items"], {"id": item_id})
        document = next((row for row in item["documents"] if isinstance(row, Mapping) and row.get("id") == document_id), None)
        if document is None:
            raise LookupError("work_document_not_found")
        if self.guardian_backed:
            object_id = str(document.get("vault_object_id") or "")
            if not object_id or self.object_store is None:
                raise LookupError("work_document_vault_object_not_found")
            self._audit_file_access("get")
            _metadata, data = self.object_store.get_bytes(object_id=object_id)
            return data, dict(document)
        path, result = self.file_path(workspace_id, item_id, document_id)
        return path.read_bytes(), result

    def interpret(self, text: str) -> dict[str, Any]:
        """Turn common natural phrasing into a reviewable booking draft.

        This deterministic fallback remains available when the selected model is
        offline. It deliberately prepares a draft; it never silently invents data.
        """
        source = " ".join(str(text or "").split())[:4000]
        lower = source.casefold()
        fields: dict[str, Any] = {"source": "Work Pilot", "status": "scheduled", "duration": 60}
        assign = re.search(r"\b(?:assign(?:ed)?\s+to|with)\s+([a-z][a-z .'-]{1,80})(?=\s+(?:at|on|for|in)\b|$)", source, re.I)
        boundary = r"(?=\s+(?:at|on|with|and|in|assign(?:ed)?\s+to|next|this|today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|$)"
        customer = re.search(r"\b(?:for|client|customer)\s+([a-z][a-z .'-]{1,80}?)" + boundary, source, re.I)
        location = re.search(r"\b(?:location(?: is)?|address(?: is)?)\s+([^,]+?)" + boundary, source, re.I)
        duration = re.search(r"\b(?:for\s+)?(\d+(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?)\b", lower)
        time_match = re.search(r"\b(?:at\s+)?([01]?\d|2[0-3])[:.]([0-5]\d)\b|\b(?:at\s+)?(1[0-2]|0?[1-9])\s*(am|pm)\b", lower)
        date = self._natural_date(lower)
        fields["assignee"] = _clean(assign.group(1), 160) if assign else ""
        fields["customer"] = _clean(customer.group(1), 160) if customer else ""
        fields["location"] = _clean(location.group(1), 240) if location else ""
        if duration:
            amount = float(duration.group(1)); fields["duration"] = int(amount * 60 if duration.group(2).startswith(("hour", "hr")) else amount)
        if time_match:
            if time_match.group(1):
                fields["time"] = f"{int(time_match.group(1)):02d}:{int(time_match.group(2)):02d}"
            else:
                hour = int(time_match.group(3)) % 12 + (12 if time_match.group(4) == "pm" else 0)
                fields["time"] = f"{hour:02d}:00"
        if date:
            fields["date"] = date
        update_verb = re.search(r"\b(cancel|reschedule|move|rebook|assign|complete|finish|change|update)\b", lower)
        create_verb = re.search(r"\b(book|schedule|create|add|arrange)\b", lower)
        if update_verb and not create_verb:
            verb = update_verb.group(1)
            if verb == "assign" and not fields.get("assignee"):
                assigned_to = re.search(r"\bassign\b.+?\bto\s+([a-z][a-z .'-]{1,80})$", source, re.I)
                if assigned_to:
                    fields["assignee"] = _clean(assigned_to.group(1), 160)
            if verb == "cancel": fields = {"status": "cancelled"}
            elif verb in {"complete", "finish"}: fields = {"status": "completed"}
            else:
                fields = {key: value for key, value in fields.items() if key in {"date", "time", "assignee"} and value}
            target = source[update_verb.end():]
            target = re.split(r"\b(?:to|on|at|with|and|assign(?:ed)?\s+to|next|this|today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", target, maxsplit=1, flags=re.I)[0]
            target = re.sub(r"^(?:the|job|work|appointment|booking|visit|for)\s+", "", target.strip(), flags=re.I)
            if not target:
                customer_target = re.search(r"\b(?:for|customer|client)\s+([a-z][a-z .'-]{1,80})", source, re.I)
                target = customer_target.group(1) if customer_target else ""
            return {
                "intent": "update_work", "query": _clean(target, 160), "fields": fields,
                "missing_fields": ["work item"] if not target else [], "ready": bool(target and fields),
                "summary": f"{verb.title()} {_clean(target, 160) or 'a work item'}",
            }
        type_map = {"appointment": "appointment", "consultation": "consultation", "survey": "survey", "quote": "survey", "visit": "visit", "meeting": "meeting", "job": "job", "installation": "job", "repair": "job"}
        fields["type"] = next((value for key, value in type_map.items() if key in lower), "job")
        title = source
        title = re.sub(r"^(?:please\s+)?(?:book|schedule|create|add|arrange)\s+(?:a|an|the)?\s*", "", title, flags=re.I)
        title = re.split(r"\b(?:for|client|customer|assign(?:ed)?\s+to|with|on|at)\b", title, maxsplit=1, flags=re.I)[0]
        fields["title"] = _clean(title, 160) or "New work"
        missing = [label for key, label in (("date", "date"), ("time", "time")) if not fields.get(key)]
        return {"intent": "create_work", "fields": fields, "missing_fields": missing, "ready": not missing, "summary": f"Prepare {fields['title']}" + (f" for {fields['customer']}" if fields["customer"] else "")}

    def conflicts(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        scheduled = [item for item in items if item.get("status") not in FINAL_STATUSES]
        for index, left in enumerate(scheduled):
            left_start, left_end = self._bounds(left)
            if not left_start:
                continue
            for right in scheduled[index + 1:]:
                shared = ({left.get("assignee")} | set(left.get("resource_ids") or [])) & ({right.get("assignee")} | set(right.get("resource_ids") or []))
                shared.discard("")
                right_start, right_end = self._bounds(right)
                if shared and right_start and left_start < right_end and right_start < left_end:
                    conflicts.append({"id": f"conflict_{left['id']}_{right['id']}", "item_ids": [left["id"], right["id"]], "resources": sorted(shared), "message": f"{', '.join(sorted(shared))} is booked on overlapping work."})
        return conflicts

    def _normalise_item(self, raw: Mapping[str, Any], actor_id: str = "") -> dict[str, Any]:
        item = deepcopy(dict(raw))
        starts = _parse_time(item.get("starts_at"))
        date = str(item.get("date") or (starts.date().isoformat() if starts else ""))[:10]
        time = str(item.get("time") or (starts.strftime("%H:%M") if starts else ""))[:5]
        duration = max(1, min(int(item.get("duration") or self._duration_from_times(item) or 60), 30 * 24 * 60))
        documents = []
        for value in item.get("documents") or []:
            documents.append(dict(value) if isinstance(value, Mapping) else {"id": f"legacy_{uuid4().hex}", "name": _safe_name(value), "kind": "legacy_reference", "created_at": ""})
        raw_estimate = item.get("cost_estimate") if isinstance(item.get("cost_estimate"), Mapping) else {}
        cost_estimate = {
            "material_cost": _money(raw_estimate.get("material_cost")),
            "labour_cost": _money(raw_estimate.get("labour_cost")),
            "external_cost": _money(raw_estimate.get("external_cost")),
            "currency": _clean(raw_estimate.get("currency") or "EUR", 8),
            "note": _clean(raw_estimate.get("note"), 1000),
            "source": _clean(raw_estimate.get("source") or "shared_work_record", 80),
            "updated_at": _clean(raw_estimate.get("updated_at"), 80),
        }
        return {
            **item, "id": _clean(item.get("id") or f"work_{uuid4().hex}", 160), "title": _clean(item.get("title"), 160),
            "customer": _clean(item.get("customer"), 160), "customer_id": _clean(item.get("customer_id"), 160),
            "customer_email": _clean(item.get("customer_email"), 240), "customer_phone": _clean(item.get("customer_phone"), 80),
            "type": _clean(item.get("type") or "job", 40), "status": str(item.get("status") or "new") if str(item.get("status") or "new") in ALLOWED_STATUSES else "new",
            "offering_id": _clean(item.get("offering_id"), 160), "cost_estimate": cost_estimate,
            "date": date, "time": time, "duration": duration, "assignee": _clean(item.get("assignee"), 160),
            "assignee_ids": [_clean(value, 160) for value in item.get("assignee_ids") or [] if _clean(value, 160)][:100],
            "resource_ids": [_clean(value, 160) for value in item.get("resource_ids") or [] if _clean(value, 160)][:100],
            "skills_required": [_clean(value, 100) for value in item.get("skills_required") or [] if _clean(value, 100)][:100],
            "location": _clean(item.get("location"), 500), "source": _clean(item.get("source") or "Back office", 80),
            "notes": str(item.get("notes") or "")[:16000], "documents": documents[:500],
            "updates": [dict(value) for value in item.get("updates") or [] if isinstance(value, Mapping)][:2000],
            "checklist": [dict(value) for value in item.get("checklist") or [] if isinstance(value, Mapping)][:500],
            "materials": [dict(value) for value in item.get("materials") or [] if isinstance(value, Mapping)][:500],
            "time_entries": [dict(value) for value in item.get("time_entries") or [] if isinstance(value, Mapping)][:2000],
            "dependencies": [_clean(value, 160) for value in item.get("dependencies") or [] if _clean(value, 160)][:100],
            "recurrence": dict(item.get("recurrence") or {}), "quote": self._commercial(item.get("quote")),
            "invoice": self._commercial(item.get("invoice")), "customer_signature": dict(item.get("customer_signature") or {}),
            "customer_requests": [dict(value) for value in item.get("customer_requests") or [] if isinstance(value, Mapping)][:500],
            "created_at": str(item.get("created_at") or _now()), "updated_at": _now() if actor_id else str(item.get("updated_at") or ""),
            "updated_by": actor_id or str(item.get("updated_by") or ""),
        }

    def _normalise_intake(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        return {**dict(raw), "id": _clean(raw.get("id") or f"intake_{uuid4().hex}", 160), "channel": _clean(raw.get("channel") or "Website", 40), "title": _clean(raw.get("title") or "Booking request", 160), "customer": _clean(raw.get("customer"), 160), "state": _clean(raw.get("state") or "Needs review", 60), "received_at": str(raw.get("received_at") or _now())}

    def _normalise_resource(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        return {**dict(raw), "id": _clean(raw.get("id") or f"resource_{uuid4().hex}", 160), "name": _clean(raw.get("name"), 160), "type": _clean(raw.get("type") or "equipment", 60), "capacity": max(1, int(raw.get("capacity") or 1)), "skills": [_clean(value, 100) for value in raw.get("skills") or [] if _clean(value, 100)], "active": bool(raw.get("active", True))}

    def _commercial(self, raw: Any) -> dict[str, Any]:
        source = dict(raw) if isinstance(raw, Mapping) else {}
        return {
            **source, "status": _clean(source.get("status") or "not_created", 40),
            "amount": _money(source.get("amount")),
            "line_items": [dict(row) for row in source.get("line_items") or [] if isinstance(row, Mapping)][:500],
        }

    def _line_items(self, rows: list[Mapping[str, Any]], *, fallback_title: str, fallback_amount: Any, default_tax: Decimal = Decimal("0")) -> list[dict[str, str]]:
        normalised: list[dict[str, str]] = []
        for row in rows[:500]:
            description = _clean(row.get("description"), 240)
            if not description:
                continue
            try:
                quantity = Decimal(str(row.get("quantity") or "1"))
                unit_price = Decimal(_money(row.get("unit_price") or "0"))
            except (InvalidOperation, ValueError) as error:
                raise ValueError("invalid_commercial_line_item") from error
            line_tax = Decimal(str(row.get("tax_rate") if row.get("tax_rate") not in (None, "") else default_tax).replace(",", "."))
            normalised.append({"description": description, "type": _clean(row.get("type") or "service", 40), "quantity": str(quantity), "unit_price": str(unit_price.quantize(Decimal("0.01"))), "tax_rate": str(line_tax)})
        if not normalised:
            normalised.append({"description": fallback_title or "Work", "type": "service", "quantity": "1", "unit_price": _money(fallback_amount or "0"), "tax_rate": str(default_tax)})
        return normalised

    def _reminder(self, item: Mapping[str, Any], fields: Mapping[str, Any], actor_id: str) -> dict[str, Any]:
        kind = _clean(fields.get("kind") or "appointment_24h", 60)
        channel = _clean(fields.get("channel") or ("email" if item.get("customer_email") else "sms" if item.get("customer_phone") else "manual"), 30)
        start = " ".join(value for value in (str(item.get("date") or ""), str(item.get("time") or "")) if value)
        message = _clean(fields.get("message") or f"Reminder: {item.get('title') or 'Your booking'} is scheduled for {start or 'the agreed time'}.", 2000)
        return {
            "id": f"reminder_{uuid4().hex}", "item_id": item.get("id"), "kind": kind,
            "channel": channel, "recipient": item.get("customer_email") or item.get("customer_phone") or item.get("customer") or "",
            "message": message, "status": "needs_approval" if channel != "manual" else "manual_action_required",
            "prepared_at": _now(), "prepared_by": actor_id,
        }

    def _customer_history(self, items: list[dict[str, Any]], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_key: dict[str, dict[str, Any]] = {}
        name_keys: dict[str, list[str]] = {}
        for source in existing:
            if not source.get("id") and not source.get("name"):
                continue
            row = dict(source)
            key = str(row.get("id") or row.get("name") or "").casefold()
            name_key = _clean(row.get("name"), 160).casefold()
            linked = set(row.get("work_item_ids") or [])
            duplicate_key = next((candidate for candidate in name_keys.get(name_key, []) if linked.intersection(by_key[candidate].get("work_item_ids") or [])), "")
            if duplicate_key:
                current = by_key[duplicate_key]
                for field in ("email", "phone", "billing_address", "address", "service_address", "contact_name", "notes", "source", "customer_type"):
                    current[field] = current.get(field) or row.get(field) or ""
                current["work_item_ids"] = sorted(set([*current.get("work_item_ids", []), *row.get("work_item_ids", [])]))
                current["last_activity_at"] = max(str(current.get("last_activity_at") or ""), str(row.get("last_activity_at") or ""))
                continue
            by_key[key] = row
            name_keys.setdefault(name_key, []).append(key)
        for item in items:
            name = _clean(item.get("customer"), 160)
            if not name:
                continue
            key = str(item.get("customer_id") or name).casefold()
            if key not in by_key:
                linked_key = next((candidate for candidate in name_keys.get(name.casefold(), []) if item["id"] in (by_key[candidate].get("work_item_ids") or [])), "")
                if linked_key:
                    key = linked_key
            row = by_key.setdefault(key, {"id": item.get("customer_id") or f"customer_{hashlib.sha256(key.encode()).hexdigest()[:16]}", "name": name})
            name_keys.setdefault(name.casefold(), []).append(key)
            row.update({
                "name": name, "email": item.get("customer_email") or row.get("email") or "",
                "phone": item.get("customer_phone") or row.get("phone") or "",
                "billing_address": item.get("customer_address") or row.get("billing_address") or row.get("address") or "",
                "address": item.get("customer_address") or row.get("address") or row.get("billing_address") or "",
                "service_address": item.get("location") or row.get("service_address") or "",
                "work_item_ids": sorted(set([*row.get("work_item_ids", []), item["id"]])),
                "last_activity_at": max(str(row.get("last_activity_at") or ""), str(item.get("updated_at") or item.get("created_at") or "")),
            })
        return list(by_key.values())[:5000]

    def _public_item(self, item: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": item.get("id"), "title": item.get("title"), "customer": item.get("customer"),
            "status": item.get("status"), "date": item.get("date"), "time": item.get("time"),
            "duration": item.get("duration"), "location": item.get("location"), "assignee": item.get("assignee"),
            "quote": item.get("quote"), "invoice": item.get("invoice"), "payment_request": item.get("payment_request"), "documents": [
                {"id": row.get("id"), "name": row.get("name"), "kind": row.get("kind")}
                for row in item.get("documents") or [] if isinstance(row, Mapping) and row.get("kind") in {"quote", "invoice", "service_report", "completion_certificate"}
            ],
        }

    def _portal_record(self, token: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
        token_hash = hashlib.sha256(str(token or "").encode()).hexdigest()
        if self.domain_store is not None:
            for record in self.domain_store.list_all("work_schedule.records"):
                if record.get("entity_id") != "schedule":
                    continue
                current = dict(record["payload"])
                access = next((row for row in current.get("portal_access", []) if row.get("token_hash") == token_hash), None)
                if access is None:
                    continue
                expires = _parse_time(access.get("expires_at"))
                if access.get("revoked") or not expires or expires <= datetime.now(UTC):
                    raise LookupError("customer_portal_access_expired")
                workspace_id = str(record["workspace_id"])
                return workspace_id, self.get(workspace_id), access
            raise LookupError("customer_portal_access_not_found")
        if self.repository is None:
            raise LookupError("customer_portal_access_not_found")
        root = Path(self.repository.base_dir)
        for path in root.glob("*/work_schedule.json"):
            workspace_id = path.parent.name
            current = self.get(workspace_id)
            access = next((row for row in current.get("portal_access", []) if row.get("token_hash") == token_hash), None)
            if access is None:
                continue
            expires = _parse_time(access.get("expires_at"))
            if access.get("revoked") or not expires or expires <= datetime.now(UTC):
                raise LookupError("customer_portal_access_expired")
            return workspace_id, current, access
        raise LookupError("customer_portal_access_not_found")

    def _mobile_job(self, item: Mapping[str, Any]) -> dict[str, Any]:
        starts = f"{item.get('date')}T{item.get('time') or '00:00'}:00"
        start_dt = _parse_time(starts)
        ends = (start_dt + timedelta(minutes=int(item.get("duration") or 60))).isoformat() if start_dt else ""
        return {**dict(item), "starts_at": starts if item.get("date") else "", "ends_at": ends, "evidence_count": len(item.get("documents") or [])}

    def _duration_from_times(self, item: Mapping[str, Any]) -> int:
        start, end = _parse_time(item.get("starts_at")), _parse_time(item.get("ends_at"))
        return max(1, int((end - start).total_seconds() // 60)) if start and end and end > start else 0

    def _bounds(self, item: Mapping[str, Any]) -> tuple[datetime | None, datetime | None]:
        start = _parse_time(f"{item.get('date')}T{item.get('time') or '00:00'}:00") if item.get("date") else None
        return (start, start + timedelta(minutes=int(item.get("duration") or 60))) if start else (None, None)

    def _find(self, items: list[dict[str, Any]], fields: Mapping[str, Any]) -> dict[str, Any]:
        item = next((row for row in items if row["id"] == str(fields.get("id") or "")), None)
        if item is None:
            raise LookupError("work_item_not_found")
        return item

    def _create_recurrences(self, items: list[dict[str, Any]], item: dict[str, Any]) -> None:
        recurrence = item.get("recurrence") or {}
        frequency, count = str(recurrence.get("frequency") or "none"), min(max(int(recurrence.get("count") or 1), 1), 52)
        if frequency not in {"daily", "weekly", "monthly"} or count <= 1 or not item.get("date"):
            return
        origin = datetime.fromisoformat(item["date"])
        series_id = f"series_{uuid4().hex}"
        item["series_id"] = series_id
        for index in range(1, count):
            if frequency == "daily": target = origin + timedelta(days=index)
            elif frequency == "weekly": target = origin + timedelta(weeks=index)
            else:
                month = origin.month - 1 + index; year = origin.year + month // 12; month = month % 12 + 1
                day = min(origin.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
                target = origin.replace(year=year, month=month, day=day)
            clone = deepcopy(item); clone.update({"id": f"work_{uuid4().hex}", "date": target.date().isoformat(), "series_index": index + 1})
            items.append(clone)

    def _natural_date(self, text: str) -> str:
        today = datetime.now().date()
        if "today" in text: return today.isoformat()
        if "tomorrow" in text: return (today + timedelta(days=1)).isoformat()
        weekdays = {name: index for index, name in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"))}
        for name, target in weekdays.items():
            if name in text:
                days = (target - today.weekday()) % 7
                if days == 0 or f"next {name}" in text: days += 7
                return (today + timedelta(days=days)).isoformat()
        match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text)
        if match:
            day, month, year = map(int, match.groups()); year += 2000 if year < 100 else 0
            try: return datetime(year, month, day).date().isoformat()
            except ValueError: return ""
        return ""

    def _write(self, workspace_id: str, model: Mapping[str, Any]) -> None:
        stored = {key: value for key, value in dict(model).items() if key != "conflicts"}
        if self.domain_store is not None:
            current = self.domain_store.get_optional(
                "work_schedule.records", workspace_id=workspace_id, entity_id="schedule"
            )
            self.domain_store.put(
                "work_schedule.records", workspace_id=workspace_id, entity_id="schedule",
                payload=stored, expected_version=int(current["version"]) if current else None,
                actor_id=self._guardian_actor(stored.get("changed_by") or "work-schedule-runtime"),
            )
            return
        path = self._path(workspace_id); temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(stored, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _guardian_actor(value: Any) -> str:
        actor = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "work-schedule-runtime")).strip(".-")
        return (actor or "work-schedule-runtime")[:120]

    def _store_file_bytes(
        self, workspace_id: str, item_id: str, *, data: bytes, filename: str,
        content_type: str, actor_id: str, legacy_stored_name: str, idempotency_key: str = "",
    ) -> dict[str, Any]:
        if self.object_store is None:
            path = self._files_dir(workspace_id, item_id) / legacy_stored_name
            path.write_bytes(data)
            return {"stored_name": legacy_stored_name}
        stable_key = self._mobile_idempotency_key(idempotency_key)
        object_id = (
            f"work-{hashlib.sha256(f'{workspace_id}:{item_id}:{stable_key}'.encode()).hexdigest()[:32]}"
            if stable_key else f"work-{uuid4().hex}"
        )
        self._audit_file_access("put")
        metadata = self.object_store.put_bytes(
            object_id=object_id, data=data, original_name=_safe_name(filename),
            content_type=content_type,
            idempotency_key=f"work-file-{stable_key}" if stable_key else f"work-file-{uuid4().hex}",
            actor_id=self._guardian_actor(actor_id), recorded_at=_now(),
        )
        return {
            "vault_object_id": object_id,
            "vault_plaintext_sha256": metadata["plaintext_sha256"],
            "vault_receipt_hash": metadata.get("receipt_hash"),
        }

    @staticmethod
    def _audit_file_access(operation: str) -> None:
        """Declare the encrypted object-store operation without exposing file identity."""

        sys.audit("tessaris.vault_domain_access", "work_schedule.files", operation)

    @staticmethod
    def _mobile_idempotency_key(value: Any) -> str:
        key = str(value or "").strip()
        if not key:
            return ""
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,200}", key):
            raise ValueError("invalid_mobile_idempotency_key")
        return key

    @staticmethod
    def _mobile_request_hash(payload: Mapping[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def _mobile_operation_replay(
        self, schedule: Mapping[str, Any], idempotency_key: str, request_hash: str,
    ) -> dict[str, Any] | None:
        key = self._mobile_idempotency_key(idempotency_key)
        if not key:
            return None
        prior = next(
            (
                dict(row) for row in schedule.get("mobile_operation_receipts") or []
                if isinstance(row, Mapping) and row.get("idempotency_key") == key
            ),
            None,
        )
        if prior is None:
            return None
        if prior.get("request_hash") != request_hash:
            raise ValueError("mobile_idempotency_key_reused_for_different_request")
        return prior

    def _append_mobile_operation_receipt(
        self, schedule: dict[str, Any], *, idempotency_key: str, request_hash: str,
        operation: str, item_id: str, actor_id: str, document_id: str = "",
    ) -> dict[str, Any] | None:
        key = self._mobile_idempotency_key(idempotency_key)
        if not key:
            return None
        receipt = {
            "idempotency_key": key, "request_hash": request_hash,
            "operation": _clean(operation, 80), "item_id": _clean(item_id, 160),
            "actor_id": self._guardian_actor(actor_id), "recorded_at": _now(),
        }
        if document_id:
            receipt["document_id"] = _clean(document_id, 160)
        schedule.setdefault("mobile_operation_receipts", []).append(receipt)
        schedule["mobile_operation_receipts"] = schedule["mobile_operation_receipts"][-5000:]
        return receipt

    def _append_schedule_audit(
        self,
        workspace_id: str,
        *,
        before_items: list[Mapping[str, Any]],
        after_items: list[Mapping[str, Any]],
        before_stock_movements: list[Mapping[str, Any]],
        after_stock_movements: list[Mapping[str, Any]],
        revision: int,
        actor_id: str,
    ) -> None:
        """Persist immutable lifecycle evidence beside the mutable schedule record."""

        if self.operational_store is None:
            return
        before = {str(row.get("id") or ""): row for row in before_items if row.get("id")}
        for item in after_items:
            item_id = str(item.get("id") or "")
            previous = before.get(item_id)
            changes: list[tuple[str, dict[str, Any]]] = []
            if previous is None:
                changes.append(("work_created", {"status": item.get("status") or "new"}))
            else:
                schedule_fields = ("date", "time", "duration", "assignee", "location")
                changed_fields = [key for key in schedule_fields if previous.get(key) != item.get(key)]
                if changed_fields:
                    changes.append(("work_rescheduled_or_assigned", {"changed_fields": changed_fields}))
                if previous.get("status") != item.get("status"):
                    changes.append(("work_status_changed", {
                        "previous_status": previous.get("status") or "",
                        "status": item.get("status") or "",
                    }))
                previous_update_ids = {
                    str(row.get("id") or "") for row in previous.get("updates") or []
                    if isinstance(row, Mapping) and row.get("id")
                }
                added_updates = [
                    str(row.get("id") or "") for row in item.get("updates") or []
                    if isinstance(row, Mapping) and row.get("id")
                    and str(row.get("id")) not in previous_update_ids
                ]
                if added_updates:
                    changes.append(("work_update_added", {
                        "update_ids": added_updates[:50], "update_count": len(added_updates),
                    }))
                previous_document_ids = {
                    str(row.get("id") or "") for row in previous.get("documents") or []
                    if isinstance(row, Mapping) and row.get("id")
                }
                added_documents = [
                    str(row.get("id") or "") for row in item.get("documents") or []
                    if isinstance(row, Mapping) and row.get("id")
                    and str(row.get("id")) not in previous_document_ids
                ]
                if added_documents:
                    changes.append(("work_evidence_added", {
                        "document_ids": added_documents[:50], "document_count": len(added_documents),
                    }))
            for sequence, (kind, detail) in enumerate(changes, start=1):
                self.operational_store.append_audit(
                    workspace_id=workspace_id,
                    department_id="operations",
                    feature_id="work_schedule",
                    event_id=f"revision-{revision}-{item_id}-{sequence}-{kind}",
                    payload={
                        "schema_version": "aion.work-schedule.audit.v1",
                        "kind": kind,
                        "work_item_id": item_id,
                        "revision": revision,
                        "at": _now(),
                        "actor_id": _clean(actor_id, 120),
                        **detail,
                    },
                    actor_id=self._guardian_actor(actor_id),
                )
        previous_movement_ids = {
            str(row.get("id") or "") for row in before_stock_movements if row.get("id")
        }
        for movement in after_stock_movements:
            movement_id = str(movement.get("id") or "")
            if not movement_id or movement_id in previous_movement_ids:
                continue
            self.operational_store.append_audit(
                workspace_id=workspace_id,
                department_id="operations",
                feature_id="work_schedule",
                event_id=f"revision-{revision}-{movement_id}-stock-movement-recorded",
                payload={
                    "schema_version": "aion.work-schedule.audit.v1",
                    "kind": "stock_movement_recorded",
                    "stock_movement_id": movement_id,
                    "inventory_item_id": str(movement.get("item_id") or ""),
                    "movement_type": str(movement.get("movement_type") or ""),
                    "revision": revision,
                    "at": _now(),
                    "actor_id": _clean(actor_id, 120),
                },
                actor_id=self._guardian_actor(actor_id),
            )

    def _quotation_pdf(
        self, title: str, item: Mapping[str, Any], commercial: Mapping[str, Any],
        profile: Mapping[str, Any], *, document_kind: str = "quote",
    ) -> bytes:
        is_invoice = document_kind == "invoice"
        document_label = "INVOICE" if is_invoice else "QUOTATION"
        business = profile.get("business") if isinstance(profile.get("business"), Mapping) else {}
        customer = profile.get("customer") if isinstance(profile.get("customer"), Mapping) else {}
        description_of_work = _clean(profile.get("description_of_work"), 4000)
        terms = _clean(profile.get("terms"), 3000) if profile.get("include_terms") else ""
        valid_days = max(1, min(int(profile.get("valid_days") or 30), 365))
        issued = datetime.now()
        valid = issued + timedelta(days=valid_days)
        accent = str(business.get("accent") or "#2563eb")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", accent): accent = "#2563eb"
        rgb = tuple(int(accent[index:index + 2], 16) / 255 for index in (1, 3, 5))
        currency = _clean(business.get("currency") or "EUR", 8)

        logo_image: tuple[bytes, int, int] | None = None
        logo_source = str(business.get("logo") or "")
        if logo_source.startswith("data:image/") and "," in logo_source:
            try:
                from io import BytesIO
                from PIL import Image

                raw_logo = base64.b64decode(logo_source.split(",", 1)[1], validate=False)
                with Image.open(BytesIO(raw_logo)) as source:
                    if source.mode in {"RGBA", "LA"} or "transparency" in source.info:
                        rgba = source.convert("RGBA")
                        white = Image.new("RGBA", rgba.size, "white")
                        white.alpha_composite(rgba)
                        converted = white.convert("RGB")
                    else:
                        converted = source.convert("RGB")
                    converted.thumbnail((420, 180))
                    output = BytesIO()
                    converted.save(output, format="JPEG", quality=92, optimize=True)
                    logo_image = (output.getvalue(), converted.width, converted.height)
            except Exception:
                logo_image = None

        def pdf_text(value: Any) -> str:
            normalised = (str(value or "")
                .replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")
                .replace("\u2018", "'").replace("\u2019", "'")
                .replace("\u201c", '"').replace("\u201d", '"').replace("\u00b7", "|")
            )
            return normalised.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        def wrap(value: Any, width: int = 82, limit: int = 6) -> list[str]:
            words, rows, row = str(value or "").split(), [], ""
            for word in words:
                candidate = f"{row} {word}".strip()
                if len(candidate) > width and row:
                    rows.append(row); row = word
                    if len(rows) >= limit: break
                else: row = candidate
            if row and len(rows) < limit: rows.append(row)
            return rows or [""]

        commands: list[str] = ["1 1 1 rg", "0 0 595 842 re f"]
        def text(value: Any, x: float, y: float, size: int = 10, bold: bool = False, white: bool = False) -> None:
            commands.extend([
                "1 1 1 rg" if white else "0.08 0.10 0.14 rg",
                "BT", f"/{'F2' if bold else 'F1'} {size} Tf", f"{x} {y} Td",
                f"({pdf_text(value)[:180]}) Tj", "ET",
            ])
        def line(x1: float, y1: float, x2: float, y2: float) -> None:
            commands.extend(["0.65 0.69 0.75 RG", "0.7 w", f"{x1} {y1} m {x2} {y2} l S"])
        def bar(y: float, label: str) -> None:
            commands.extend([f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} rg", f"40 {y} 515 20 re f", "1 1 1 rg"])
            text(label, 48, y + 6, 9, True, True)

        business_x = 118 if logo_image else 40
        if logo_image:
            _logo_bytes, logo_width, logo_height = logo_image
            draw_width = 66.0
            draw_height = min(42.0, draw_width * logo_height / max(logo_width, 1))
            commands.append(f"q {draw_width:.2f} 0 0 {draw_height:.2f} 40 {793 - draw_height:.2f} cm /Im1 Do Q")
        text(business.get("name") or "Business", business_x, 795, 17, True)
        y = 778
        for value in (business.get("address"), business.get("phone"), business.get("email"), business.get("website")):
            if value: text(value, business_x, y, 8); y -= 12
        text(document_label, 390, 795, 23, True)
        text(f"{document_label} NUMBER", 365, 765, 7, True); text(commercial.get("number"), 455, 765, 9, True)
        text("DATE", 365, 748, 7, True); text(issued.strftime("%d/%m/%Y"), 455, 748, 9)
        if is_invoice:
            text("SOURCE QUOTE", 365, 731, 7, True); text(profile.get("source_quote_number") or "-", 455, 731, 9)
        else:
            text("VALID UNTIL", 365, 731, 7, True); text(valid.strftime("%d/%m/%Y"), 455, 731, 9)
        line(40, 710, 555, 710)

        bar(680, f"{document_label} FOR")
        text(customer.get("name") or item.get("customer") or "Customer details required", 48, 660, 11, True)
        text(customer.get("address") or item.get("customer_address") or item.get("location") or "", 48, 644, 9)
        text(" | ".join(filter(None, [str(customer.get("phone") or ""), str(customer.get("email") or "")])), 48, 630, 9)
        bar(594, "PAYMENT FOR" if is_invoice else "DESCRIPTION OF WORK")
        scope_y = 574
        for row in wrap(item.get("title"), 88, 2): text(row, 48, scope_y, 10, True); scope_y -= 14
        for row in wrap(description_of_work or "Scope to be confirmed in the draft quotation.", 96, 5): text(row, 48, scope_y, 8); scope_y -= 12

        table_top = 515
        commands.extend(["0.93 0.95 0.97 rg", f"40 {table_top} 515 22 re f"])
        text("DESCRIPTION", 48, table_top + 7, 8, True); text("QTY", 365, table_top + 7, 8, True); text("UNIT PRICE", 405, table_top + 7, 8, True); text("VAT", 475, table_top + 7, 8, True); text("AMOUNT", 515, table_top + 7, 8, True)
        row_y = table_top - 22
        for row in commercial.get("line_items") or []:
            quantity, unit = str(row.get("quantity") or "1"), str(row.get("unit_price") or "0.00")
            amount = (Decimal(quantity) * Decimal(unit)).quantize(Decimal("0.01"))
            text(row.get("description"), 48, row_y + 7, 8); text(quantity, 370, row_y + 7, 8); text(unit, 415, row_y + 7, 8); text(f"{row.get('tax_rate') or 0}%", 478, row_y + 7, 8); text(str(amount), 515, row_y + 7, 8)
            line(40, row_y, 555, row_y); row_y -= 22
        totals_y = min(row_y - 12, 445)
        for label, value, bold in (("SUBTOTAL", commercial.get("subtotal"), False), (f"TAX ({commercial.get('tax_rate')}%)", commercial.get("tax"), False), (f"TOTAL {document_label}", commercial.get("total"), True)):
            if bold:
                commands.extend([f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} rg", f"370 {totals_y - 4} 185 22 re f", "1 1 1 rg"])
            text(label, 385, totals_y + 3, 9, True); text(value, 510, totals_y + 3, 9, bold); totals_y -= 24
        payment_rows = ([profile.get("payment_stage")] if is_invoice and isinstance(profile.get("payment_stage"), Mapping) else [row for row in profile.get("payment_schedule") or [] if isinstance(row, Mapping)])
        payment_y = min(totals_y - 12, 350)
        if payment_rows or profile.get("payment_reference"):
            bar(payment_y, "PAYMENT DETAILS" if is_invoice else "PAYMENT SCHEDULE"); payment_y -= 17
            for payment in payment_rows[:4]:
                label = _clean(payment.get("label") or "Payment", 60)
                amount = _money(payment.get("calculated_amount") or payment.get("amount") or "0")
                due_type = _clean(payment.get("due_type"), 30)
                due = "when accepted" if due_type == "acceptance" else "on completion" if due_type == "completion" else f"{payment.get('due_value') or 0} days after acceptance" if due_type == "days" else str(payment.get("due") or payment.get("due_value") or "date to be agreed")
                text(f"{label}: {currency} {amount} - {due}", 48, payment_y, 7); payment_y -= 10
            text(f"Payment reference: {profile.get('payment_reference') or commercial.get('number')}", 48, payment_y, 7, True); payment_y -= 14
            payment_method = _clean(commercial.get("payment_method") or profile.get("payment_method") or "bank_transfer", 40)
            bank = business.get("bank") if isinstance(business.get("bank"), Mapping) else {}
            if is_invoice and payment_method in {"bank_transfer", "customer_choice"} and bank:
                bank_rows = [
                    ("Account name", bank.get("accountName")),
                    ("Bank", bank.get("bankName")),
                    ("Sort code / routing number", bank.get("sortCode")),
                    ("Account number", bank.get("accountNumber")),
                    ("IBAN", bank.get("iban")),
                    ("BIC / SWIFT", bank.get("bic")),
                ]
                bank_rows = [(label, value) for label, value in bank_rows if value]
                if bank_rows:
                    text("BANK TRANSFER DETAILS", 48, payment_y, 8, True); payment_y -= 11
                    for label, value in bank_rows:
                        text(f"{label}: {value}", 48, payment_y, 8); payment_y -= 11
            payment_links = business.get("paymentLinks") if isinstance(business.get("paymentLinks"), Mapping) else {}
            provider_links = {
                "stripe": payment_links.get("stripe") or business.get("stripePaymentLink") or business.get("stripe_payment_link"),
                "paypal": payment_links.get("paypal") or business.get("paypalPaymentLink") or business.get("paypal_payment_link"),
                "square": payment_links.get("square") or business.get("squarePaymentLink") or business.get("square_payment_link"),
                "gocardless": payment_links.get("gocardless") or business.get("gocardlessPaymentLink") or business.get("gocardless_payment_link"),
                "revolut": payment_links.get("revolut") or business.get("revolutPaymentLink") or business.get("revolut_payment_link"),
                "sumup": payment_links.get("sumup") or business.get("sumupPaymentLink") or business.get("sumup_payment_link"),
                "mollie": payment_links.get("mollie") or business.get("molliePaymentLink") or business.get("mollie_payment_link"),
                "braintree": payment_links.get("braintree") or business.get("braintreePaymentLink") or business.get("braintree_payment_link"),
                "worldpay": payment_links.get("worldpay") or business.get("worldpayPaymentLink") or business.get("worldpay_payment_link"),
                "adyen": payment_links.get("adyen") or business.get("adyenPaymentLink") or business.get("adyen_payment_link"),
                "checkout_com": payment_links.get("checkout_com") or business.get("checkoutComPaymentLink") or business.get("checkout_com_payment_link"),
            }
            online_link = _clean(provider_links.get(payment_method) or (next((value for value in provider_links.values() if value), "") if payment_method == "customer_choice" else ""), 180)
            if is_invoice and payment_method in {"stripe", "paypal", "square", "gocardless", "revolut", "sumup", "mollie", "braintree", "worldpay", "adyen", "checkout_com", "customer_choice"} and online_link:
                text("ONLINE PAYMENT", 48, payment_y, 7, True); payment_y -= 10
                for row in wrap(f"Pay securely online: {online_link}", 100, 2):
                    text(row, 48, payment_y, 7); payment_y -= 10
        if terms:
            terms_y = min(payment_y - 8, 350); bar(terms_y, "TERMS & CONDITIONS"); terms_y -= 17
            for row in wrap(terms, 108, 8): text(row, 48, terms_y, 7); terms_y -= 10
        text(
            f"Invoice for accepted quotation {profile.get('source_quote_number') or ''}." if is_invoice
            else "Draft quotation - review and approve before sending.",
            170, 34, 7,
        )

        stream = "\n".join(commands).encode("latin-1", "replace")
        image_resource = b" /XObject << /Im1 7 0 R >>" if logo_image else b""
        page = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R /F2 6 0 R >>" + image_resource + b" >> /Contents 4 0 R >>"
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", page, b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"]
        if logo_image:
            logo_bytes, logo_width, logo_height = logo_image
            objects.append(
                f"<< /Type /XObject /Subtype /Image /Width {logo_width} /Height {logo_height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(logo_bytes)} >>\nstream\n".encode()
                + logo_bytes + b"\nendstream"
            )
        output = bytearray(b"%PDF-1.4\n"); offsets = [0]
        for index, obj in enumerate(objects, 1): offsets.append(len(output)); output.extend(f"{index} 0 obj\n".encode()); output.extend(obj); output.extend(b"\nendobj\n")
        xref = len(output); output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
        for offset in offsets[1:]: output.extend(f"{offset:010d} 00000 n \n".encode())
        output.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        return bytes(output)

    def _simple_pdf(self, lines: list[str]) -> bytes:
        escaped = [str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:110] for line in lines]
        commands = ["BT", "/F1 16 Tf", "50 790 Td"]
        for index, line in enumerate(escaped):
            if index == 1: commands.append("/F1 10 Tf")
            commands.extend([f"({line}) Tj", "0 -22 Td"])
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", "replace")
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>", b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
        output = bytearray(b"%PDF-1.4\n"); offsets = [0]
        for index, obj in enumerate(objects, 1): offsets.append(len(output)); output.extend(f"{index} 0 obj\n".encode()); output.extend(obj); output.extend(b"\nendobj\n")
        xref = len(output); output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
        for offset in offsets[1:]: output.extend(f"{offset:010d} 00000 n \n".encode())
        output.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        return bytes(output)
