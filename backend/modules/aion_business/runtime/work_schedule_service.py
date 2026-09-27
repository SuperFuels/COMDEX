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
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository


FINAL_STATUSES = {"cancelled", "completed", "invoiced", "paid"}
ALLOWED_STATUSES = {
    "new", "quote_required", "awaiting_approval", "scheduled", "on_way", "en_route",
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

    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()

    def _dir(self, workspace_id: str) -> Path:
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
            "document_counters": {"quote": 0, "invoice": 0},
        }

    def get(self, workspace_id: str) -> dict[str, Any]:
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
            "document_counters": dict(payload.get("document_counters") or current.get("document_counters") or {}),
            "changed_by": _clean(changed_by, 120),
        })
        model["customers"] = self._customer_history(items, model["customers"])
        model["jobs"] = [self._mobile_job(item) for item in items]
        self._write(workspace_id, model)
        model["conflicts"] = self.conflicts(items)
        return model

    def action(self, workspace_id: str, operation: str, fields: Mapping[str, Any], *, actor_id: str) -> dict[str, Any]:
        current = self.get(workspace_id)
        payload = deepcopy(current)
        items = payload["items"]
        operation = str(operation or "").strip().casefold()
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
        return self.save(workspace_id, payload, expected_revision=current["revision"], changed_by=actor_id)

    def create_intake(self, workspace_id: str, fields: Mapping[str, Any], *, channel: str = "website") -> dict[str, Any]:
        current = self.get(workspace_id)
        current["intake"].append(self._normalise_intake({**dict(fields), "channel": channel, "received_at": _now()}))
        return self.save(workspace_id, current, expected_revision=current["revision"], changed_by=f"{channel}_booking")

    def upload(self, workspace_id: str, item_id: str, *, filename: str, content_type: str, data_base64: str, actor_id: str) -> dict[str, Any]:
        current = self.get(workspace_id)
        item = self._find(current["items"], {"id": item_id})
        try:
            content = base64.b64decode(data_base64, validate=True)
        except Exception as error:
            raise ValueError("invalid_file_encoding") from error
        if not content or len(content) > 20 * 1024 * 1024:
            raise ValueError("file_size_must_be_between_1_byte_and_20mb")
        stored_name = f"{uuid4().hex[:10]}-{_safe_name(filename)}"
        path = self._files_dir(workspace_id, item_id) / stored_name
        path.write_bytes(content)
        document = {
            "id": f"document_{uuid4().hex}", "name": _safe_name(filename), "stored_name": stored_name,
            "content_type": _clean(content_type or "application/octet-stream", 120), "size": len(content),
            "created_at": _now(), "created_by": actor_id, "kind": "evidence",
        }
        item["documents"].append(document)
        saved = self.save(workspace_id, current, expected_revision=current["revision"], changed_by=actor_id)
        return {"schedule": saved, "document": document}

    def generate_document(
        self, workspace_id: str, item_id: str, kind: str, *, actor_id: str,
        line_items: list[Mapping[str, Any]] | None = None, tax_rate: Any = "0",
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
            rows = self._line_items(line_items or [], fallback_title=item["title"], fallback_amount=(item.get(kind) or {}).get("amount"))
            subtotal = sum((Decimal(row["quantity"]) * Decimal(row["unit_price"]) for row in rows), Decimal("0"))
            rate = Decimal(str(tax_rate or "0").replace(",", "."))
            tax = (subtotal * rate / Decimal("100")).quantize(Decimal("0.01"))
            total = (subtotal + tax).quantize(Decimal("0.01"))
            commercial = {
                "status": "draft", "number": number, "line_items": rows,
                "subtotal": str(subtotal.quantize(Decimal("0.01"))), "tax_rate": str(rate),
                "tax": str(tax), "total": str(total), "amount": str(total), "created_at": _now(),
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
        path = self._files_dir(workspace_id, item_id) / stored_name
        path.write_bytes(self._simple_pdf(lines))
        document = {"id": f"document_{uuid4().hex}", "name": filename, "stored_name": stored_name, "content_type": "application/pdf", "size": path.stat().st_size, "created_at": _now(), "created_by": actor_id, "kind": kind}
        item["documents"].append(document)
        item["updates"].append({"id": f"update_{uuid4().hex}", "text": f"{title} generated and attached.", "at": _now(), "by": actor_id})
        saved = self.save(workspace_id, current, expected_revision=current["revision"], changed_by=actor_id)
        return {"schedule": saved, "document": document, "commercial": commercial}

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
        if operation == "request_reschedule":
            request.update({"requested_date": _clean(fields.get("date"), 10), "requested_time": _clean(fields.get("time"), 5)})
        elif operation == "approve_quote":
            item["quote"] = {**item["quote"], "status": "customer_approved", "approved_at": _now()}
            item["status"] = "scheduled" if item.get("date") else "new"
            request["status"] = "accepted"
        elif operation == "decline_quote":
            item["quote"] = {**item["quote"], "status": "customer_declined", "declined_at": _now()}
            request["status"] = "accepted"
        item.setdefault("customer_requests", []).append(request)
        item["updates"].append({"id": f"update_{uuid4().hex}", "text": f"Customer portal: {operation.replace('_', ' ')}.", "at": _now(), "by": "customer_portal"})
        saved = self.save(workspace_id, current, expected_revision=current["revision"], changed_by="customer_portal")
        return {"schedule": saved, "request": request, "item": self._public_item(self._find(saved["items"], {"id": item["id"]}))}

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
        item = self._find(self.get(workspace_id)["items"], {"id": item_id})
        document = next((row for row in item["documents"] if isinstance(row, Mapping) and row.get("id") == document_id), None)
        if document is None:
            raise LookupError("work_document_not_found")
        path = self._files_dir(workspace_id, item_id) / _safe_name(document.get("stored_name"))
        if not path.is_file():
            raise LookupError("work_document_file_not_found")
        return path, dict(document)

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
        return {
            **item, "id": _clean(item.get("id") or f"work_{uuid4().hex}", 160), "title": _clean(item.get("title"), 160),
            "customer": _clean(item.get("customer"), 160), "customer_id": _clean(item.get("customer_id"), 160),
            "customer_email": _clean(item.get("customer_email"), 240), "customer_phone": _clean(item.get("customer_phone"), 80),
            "type": _clean(item.get("type") or "job", 40), "status": str(item.get("status") or "new") if str(item.get("status") or "new") in ALLOWED_STATUSES else "new",
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

    def _line_items(self, rows: list[Mapping[str, Any]], *, fallback_title: str, fallback_amount: Any) -> list[dict[str, str]]:
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
            normalised.append({"description": description, "quantity": str(quantity), "unit_price": str(unit_price.quantize(Decimal("0.01")))})
        if not normalised:
            normalised.append({"description": fallback_title or "Work", "quantity": "1", "unit_price": _money(fallback_amount or "0")})
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
        by_key = {str(row.get("id") or row.get("name") or "").casefold(): dict(row) for row in existing if row.get("id") or row.get("name")}
        for item in items:
            name = _clean(item.get("customer"), 160)
            if not name:
                continue
            key = str(item.get("customer_id") or name).casefold()
            row = by_key.setdefault(key, {"id": item.get("customer_id") or f"customer_{hashlib.sha256(key.encode()).hexdigest()[:16]}", "name": name})
            row.update({
                "name": name, "email": item.get("customer_email") or row.get("email") or "",
                "phone": item.get("customer_phone") or row.get("phone") or "",
                "work_item_ids": sorted(set([*row.get("work_item_ids", []), item["id"]])),
                "last_activity_at": max(str(row.get("last_activity_at") or ""), str(item.get("updated_at") or item.get("created_at") or "")),
            })
        return list(by_key.values())[:5000]

    def _public_item(self, item: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": item.get("id"), "title": item.get("title"), "customer": item.get("customer"),
            "status": item.get("status"), "date": item.get("date"), "time": item.get("time"),
            "duration": item.get("duration"), "location": item.get("location"), "assignee": item.get("assignee"),
            "quote": item.get("quote"), "documents": [
                {"id": row.get("id"), "name": row.get("name"), "kind": row.get("kind")}
                for row in item.get("documents") or [] if isinstance(row, Mapping) and row.get("kind") in {"quote", "invoice", "service_report", "completion_certificate"}
            ],
        }

    def _portal_record(self, token: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
        token_hash = hashlib.sha256(str(token or "").encode()).hexdigest()
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
        path = self._path(workspace_id); temporary = path.with_suffix(".tmp")
        stored = {key: value for key, value in dict(model).items() if key != "conflicts"}
        temporary.write_text(json.dumps(stored, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)

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
