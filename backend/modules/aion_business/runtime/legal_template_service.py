"""Encrypted, versioned Legal templates with exact-hash professional approval."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import threading
from typing import Any, Callable, Mapping
from uuid import uuid4

from backend.modules.aion_business.runtime.legal_secure_storage import LegalEncryptedStore, LegalKeyStore
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.legal_resource_limits import (
    bounded_record_paths,
    ensure_workspace_record_write,
    estimated_encrypted_record_bytes,
)


class LegalTemplateError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class LegalTemplateService:
    """Keeps draft language separate from exact versions approved by a qualified reviewer."""

    SCHEMA_VERSION = "tessaris.legal-template.v1"
    TEMPLATE_TYPES = {
        "CUSTOMER_AGREEMENT", "SUPPLIER_AGREEMENT", "CONTRACTOR_AGREEMENT",
        "EMPLOYMENT_DOCUMENT", "TERMS_AND_CONDITIONS", "PRIVACY_NOTICE",
        "DATA_PROCESSING_AGREEMENT", "OTHER",
    }
    VARIABLE_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]{0,63})\}\}")
    MAX_CONTENT_CHARS = 500_000
    MAX_VARIABLES = 128
    MAX_VALUE_CHARS = 20_000
    MAX_VALUE_CHARS_TOTAL = 500_000
    MAX_RENDERED_CHARS = 1_000_000
    MIN_REVIEW_INTERVAL_DAYS = 1
    MAX_REVIEW_INTERVAL_DAYS = 1_825

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        clock: Callable[[], datetime] = _utc_now,
        key_store: LegalKeyStore | None = None,
    ) -> None:
        self.root = Path(root) if root else AIONBusinessPaths.LEGAL_TEMPLATES
        self.clock = clock
        self._lock = threading.RLock()
        self.key_store = key_store or LegalKeyStore(self.root)
        self.store = LegalEncryptedStore(self.root, purpose="template_records", key_store=self.key_store)

    def list_templates(self, workspace_id: str) -> list[dict[str, Any]]:
        workspace = self._component(workspace_id, "workspace_id")
        self.enforce_review_schedule(workspace)
        folder = self.root / workspace
        paths = bounded_record_paths(
            folder, ("template-*.enc",), error_type=LegalTemplateError,
        )
        records = [self._public(self.store.read(path, workspace_id=workspace, record_id=path.stem), include_content=False)
                   for path in paths]
        records.sort(key=lambda item: (item["title"].lower(), -int(item["version"])))
        return records

    def get_template(self, workspace_id: str, template_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, template_id)
            if self._expire_review_if_due(record):
                self._save(record)
        return self._public(record)

    def create_draft(
        self,
        workspace_id: str,
        *,
        title: str,
        template_type: str,
        jurisdiction: Mapping[str, Any],
        content: str,
        intended_use: str,
        actor_id: str,
        source_template_id: str = "",
    ) -> dict[str, Any]:
        workspace = self._component(workspace_id, "workspace_id")
        clean_title = " ".join(str(title or "").split()).strip()
        clean_content = str(content or "").replace("\x00", "").strip()
        kind = str(template_type or "").strip().upper().replace(" ", "_")
        if not clean_title:
            raise LegalTemplateError("template_title_required")
        if kind not in self.TEMPLATE_TYPES:
            raise LegalTemplateError("unsupported_template_type")
        if not clean_content:
            raise LegalTemplateError("template_content_required")
        if len(clean_content) > self.MAX_CONTENT_CHARS:
            raise LegalTemplateError("template_content_too_large")
        legal_context = self._jurisdiction(jurisdiction)
        variables = sorted(set(self.VARIABLE_RE.findall(clean_content)))
        if len(variables) > self.MAX_VARIABLES:
            raise LegalTemplateError("template_variable_limit_exceeded")
        source = self._load(workspace, source_template_id) if source_template_id else None
        if source and source.get("family_id") is None:
            raise LegalTemplateError("template_family_invalid")
        family_id = source["family_id"] if source else f"template-family-{uuid4().hex}"
        version = self._next_version(workspace, family_id)
        now = _iso(self.clock())
        template_id = f"template-{uuid4().hex}"
        digest = sha256(clean_content.encode("utf-8")).hexdigest()
        record = {
            "schema_version": self.SCHEMA_VERSION,
            "workspace_id": workspace,
            "template_id": template_id,
            "family_id": family_id,
            "version": version,
            "title": clean_title[:240],
            "template_type": kind,
            "jurisdiction": legal_context,
            "intended_use": str(intended_use or "").strip()[:2000],
            "content": clean_content,
            "content_sha256": digest,
            "variables": variables,
            "status": "DRAFT_REQUIRES_QUALIFIED_REVIEW",
            "approval": None,
            "approval_history": [],
            "withdrawal": None,
            "supersedes_template_id": source["template_id"] if source else None,
            "superseded_by_template_id": None,
            "created_at": now,
            "updated_at": now,
            "created_by": str(actor_id or "unknown")[:160],
            "audit_events": [],
        }
        self._event(record, "TEMPLATE_DRAFT_CREATED", actor_id, {
            "content_sha256": digest, "version": version,
            "supersedes_template_id": record["supersedes_template_id"],
        })
        with self._lock:
            self._save(record)
        return self._public(record)

    def approve(
        self,
        workspace_id: str,
        template_id: str,
        *,
        actor_id: str,
        expected_content_sha256: str,
        reviewer_name: str,
        reviewer_qualification: str,
        review_scope: str,
        approved_jurisdiction: str,
        acknowledge_qualified_review: bool,
        review_interval_days: int = 365,
    ) -> dict[str, Any]:
        if not acknowledge_qualified_review:
            raise LegalTemplateError("qualified_review_acknowledgement_required")
        reviewer = " ".join(str(reviewer_name or "").split()).strip()
        qualification = " ".join(str(reviewer_qualification or "").split()).strip()
        scope = str(review_scope or "").strip()
        approved_for = " ".join(str(approved_jurisdiction or "").split()).strip()
        if not all((reviewer, qualification, scope, approved_for)):
            raise LegalTemplateError("qualified_reviewer_details_required")
        with self._lock:
            record = self._load(workspace_id, template_id)
            if record["status"] != "DRAFT_REQUIRES_QUALIFIED_REVIEW":
                raise LegalTemplateError("template_not_approvable")
            supplied = str(expected_content_sha256 or "").lower()
            if supplied != record["content_sha256"]:
                raise LegalTemplateError("template_approval_hash_mismatch")
            approval = self._approval_record(
                record,
                actor_id=actor_id,
                reviewer=reviewer,
                qualification=qualification,
                scope=scope,
                approved_for=approved_for,
                review_interval_days=review_interval_days,
            )
            record["approval"] = approval
            record["approval_history"] = list(record.get("approval_history") or []) + [deepcopy(approval)]
            record["withdrawal"] = None
            record["status"] = "APPROVED_FOR_CONTROLLED_USE"
            record["updated_at"] = approval["approved_at"]
            self._event(record, "TEMPLATE_APPROVED", actor_id, approval)
            self._save(record)
            if record.get("supersedes_template_id"):
                previous = self._load(workspace_id, record["supersedes_template_id"])
                if previous["family_id"] != record["family_id"]:
                    raise LegalTemplateError("template_family_mismatch")
                previous["status"] = "SUPERSEDED"
                previous["superseded_by_template_id"] = record["template_id"]
                previous["updated_at"] = record["updated_at"]
                self._event(previous, "TEMPLATE_SUPERSEDED", actor_id, {
                    "superseded_by_template_id": record["template_id"],
                })
                self._save(previous)
        return self._public(record)

    def renew_review(
        self,
        workspace_id: str,
        template_id: str,
        *,
        actor_id: str,
        expected_content_sha256: str,
        reviewer_name: str,
        reviewer_qualification: str,
        review_scope: str,
        approved_jurisdiction: str,
        acknowledge_qualified_review: bool,
        review_interval_days: int = 365,
    ) -> dict[str, Any]:
        if not acknowledge_qualified_review:
            raise LegalTemplateError("qualified_review_acknowledgement_required")
        reviewer = " ".join(str(reviewer_name or "").split()).strip()
        qualification = " ".join(str(reviewer_qualification or "").split()).strip()
        scope = str(review_scope or "").strip()
        approved_for = " ".join(str(approved_jurisdiction or "").split()).strip()
        if not all((reviewer, qualification, scope, approved_for)):
            raise LegalTemplateError("qualified_reviewer_details_required")
        with self._lock:
            record = self._load(workspace_id, template_id)
            if record["status"] not in {
                "APPROVED_FOR_CONTROLLED_USE",
                "REVIEW_OVERDUE_REQUIRES_QUALIFIED_REVIEW",
                "WITHDRAWN_FOR_LEGAL_CHANGE",
            }:
                raise LegalTemplateError("template_not_reviewable")
            if str(expected_content_sha256 or "").lower() != record["content_sha256"]:
                raise LegalTemplateError("template_approval_hash_mismatch")
            approval = self._approval_record(
                record,
                actor_id=actor_id,
                reviewer=reviewer,
                qualification=qualification,
                scope=scope,
                approved_for=approved_for,
                review_interval_days=review_interval_days,
            )
            record["approval"] = approval
            record["approval_history"] = list(record.get("approval_history") or []) + [deepcopy(approval)]
            record["status"] = "APPROVED_FOR_CONTROLLED_USE"
            record["withdrawal"] = None
            record["updated_at"] = approval["approved_at"]
            self._event(record, "TEMPLATE_QUALIFIED_REVIEW_RENEWED", actor_id, approval)
            self._save(record)
        return self._public(record)

    def withdraw_for_legal_change(
        self,
        workspace_id: str,
        template_id: str,
        *,
        actor_id: str,
        reason: str,
        legal_change_reference: str,
        acknowledge_withdrawal: bool,
    ) -> dict[str, Any]:
        if not acknowledge_withdrawal:
            raise LegalTemplateError("template_withdrawal_acknowledgement_required")
        clean_reason = " ".join(str(reason or "").split()).strip()
        reference = " ".join(str(legal_change_reference or "").split()).strip()
        if not clean_reason or not reference:
            raise LegalTemplateError("template_withdrawal_reason_and_reference_required")
        with self._lock:
            record = self._load(workspace_id, template_id)
            if record["status"] not in {
                "APPROVED_FOR_CONTROLLED_USE",
                "REVIEW_OVERDUE_REQUIRES_QUALIFIED_REVIEW",
            }:
                raise LegalTemplateError("template_not_withdrawable")
            withdrawal = {
                "withdrawal_id": f"template-withdrawal-{uuid4().hex}",
                "reason": clean_reason[:2000],
                "legal_change_reference": reference[:1000],
                "withdrawn_at": _iso(self.clock()),
                "withdrawn_by_actor_id": str(actor_id or "unknown")[:160],
                "content_sha256": record["content_sha256"],
                "replacement_required": True,
            }
            record["status"] = "WITHDRAWN_FOR_LEGAL_CHANGE"
            record["withdrawal"] = withdrawal
            record["updated_at"] = withdrawal["withdrawn_at"]
            self._event(record, "TEMPLATE_WITHDRAWN_FOR_LEGAL_CHANGE", actor_id, withdrawal)
            self._save(record)
        return self._public(record)

    def enforce_review_schedule(
        self,
        workspace_id: str,
        *,
        as_of: datetime | None = None,
        actor_id: str = "system:legal-template-review-scheduler",
    ) -> dict[str, Any]:
        workspace = self._component(workspace_id, "workspace_id")
        paths = bounded_record_paths(
            self.root / workspace, ("template-*.enc",), error_type=LegalTemplateError,
        )
        checked = expired = 0
        with self._lock:
            for path in paths:
                record = self.store.read(path, workspace_id=workspace, record_id=path.stem)
                checked += 1
                if self._expire_review_if_due(record, as_of=as_of, actor_id=actor_id):
                    self._save(record)
                    expired += 1
        return {
            "workspace_id": workspace,
            "checked": checked,
            "withdrawn_for_overdue_review": expired,
            "as_of": _iso(as_of or self.clock()),
            "fail_closed": True,
        }

    def instantiate(
        self,
        workspace_id: str,
        template_id: str,
        *,
        actor_id: str,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, template_id)
            if self._expire_review_if_due(record):
                self._save(record)
        if record["status"] != "APPROVED_FOR_CONTROLLED_USE":
            raise LegalTemplateError("only_approved_template_versions_can_be_instantiated")
        approval = dict(record.get("approval") or {})
        if approval.get("content_sha256") != record["content_sha256"]:
            raise LegalTemplateError("template_approval_binding_invalid")
        raw_values = dict(values or {})
        if len(raw_values) > self.MAX_VARIABLES:
            raise LegalTemplateError("template_variable_limit_exceeded")
        clean_values: dict[str, str] = {}
        total_value_chars = 0
        for key, value in raw_values.items():
            clean_key = str(key)
            if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", clean_key):
                raise LegalTemplateError("template_variable_name_invalid")
            clean_value = str(value)
            if len(clean_value) > self.MAX_VALUE_CHARS:
                raise LegalTemplateError("template_variable_value_too_large")
            total_value_chars += len(clean_value)
            if total_value_chars > self.MAX_VALUE_CHARS_TOTAL:
                raise LegalTemplateError("template_variable_values_too_large")
            clean_values[clean_key] = clean_value
        required = set(record["variables"])
        supplied = set(clean_values)
        if supplied - required:
            raise LegalTemplateError("unknown_template_variable")
        missing = sorted(key for key in required if not clean_values.get(key, "").strip())
        if missing:
            raise LegalTemplateError("required_template_variable_missing:" + ",".join(missing))
        rendered = record["content"]
        for name in record["variables"]:
            rendered = rendered.replace("{{" + name + "}}", clean_values[name])
            if len(rendered) > self.MAX_RENDERED_CHARS:
                raise LegalTemplateError("rendered_template_too_large")
        rendered_hash = sha256(rendered.encode("utf-8")).hexdigest()
        return {
            "schema_version": "tessaris.legal-template-instance.v1",
            "instance_id": f"template-instance-{uuid4().hex}",
            "workspace_id": record["workspace_id"],
            "template_id": record["template_id"],
            "template_family_id": record["family_id"],
            "template_version": record["version"],
            "template_content_sha256": record["content_sha256"],
            "approval_id": approval["approval_id"],
            "rendered_content": rendered,
            "rendered_content_sha256": rendered_hash,
            "created_at": _iso(self.clock()),
            "created_by": str(actor_id or "unknown")[:160],
            "status": "CONTROLLED_DRAFT_REQUIRES_FINAL_HUMAN_REVIEW",
            "external_delivery_authorized": False,
            "not_legal_advice": True,
            "template_review_due_at": approval.get("review_due_at"),
        }

    def _approval_record(
        self,
        record: Mapping[str, Any],
        *,
        actor_id: str,
        reviewer: str,
        qualification: str,
        scope: str,
        approved_for: str,
        review_interval_days: int,
    ) -> dict[str, Any]:
        interval = int(review_interval_days)
        if not self.MIN_REVIEW_INTERVAL_DAYS <= interval <= self.MAX_REVIEW_INTERVAL_DAYS:
            raise LegalTemplateError("template_review_interval_invalid")
        approved_at = self.clock()
        return {
            "approval_id": f"template-approval-{uuid4().hex}",
            "content_sha256": record["content_sha256"],
            "reviewer_name": reviewer[:240],
            "reviewer_qualification": qualification[:500],
            "review_scope": scope[:5000],
            "approved_jurisdiction": approved_for[:500],
            "approved_at": _iso(approved_at),
            "review_interval_days": interval,
            "review_due_at": _iso(approved_at + timedelta(days=interval)),
            "approved_by_actor_id": str(actor_id or "unknown")[:160],
            "qualified_review_asserted_by_user": True,
            "tessaris_legal_approval_claim": False,
        }

    def _expire_review_if_due(
        self,
        record: dict[str, Any],
        *,
        as_of: datetime | None = None,
        actor_id: str = "system:legal-template-review-scheduler",
    ) -> bool:
        if record.get("status") != "APPROVED_FOR_CONTROLLED_USE":
            return False
        approval = dict(record.get("approval") or {})
        due_raw = str(approval.get("review_due_at") or "")
        try:
            due = datetime.fromisoformat(due_raw.replace("Z", "+00:00"))
        except ValueError:
            # Legacy approved records without a valid schedule fail closed.
            due = datetime.min.replace(tzinfo=timezone.utc)
        now = as_of or self.clock()
        if due > now:
            return False
        withdrawal = {
            "withdrawal_id": f"template-withdrawal-{uuid4().hex}",
            "reason": "Scheduled qualified-review deadline reached",
            "legal_change_reference": "scheduled-review-policy",
            "withdrawn_at": _iso(now),
            "withdrawn_by_actor_id": str(actor_id or "unknown")[:160],
            "content_sha256": record["content_sha256"],
            "replacement_required": False,
        }
        record["status"] = "REVIEW_OVERDUE_REQUIRES_QUALIFIED_REVIEW"
        record["withdrawal"] = withdrawal
        record["updated_at"] = withdrawal["withdrawn_at"]
        self._event(record, "TEMPLATE_WITHDRAWN_FOR_OVERDUE_REVIEW", actor_id, withdrawal)
        return True

    def _next_version(self, workspace_id: str, family_id: str) -> int:
        versions = []
        for item in self.list_templates(workspace_id):
            if item.get("family_id") == family_id:
                versions.append(int(item.get("version") or 0))
        return max(versions, default=0) + 1

    @staticmethod
    def _jurisdiction(value: Mapping[str, Any]) -> dict[str, Any]:
        country = str(value.get("country_code") or "").strip().upper()
        governing_law = " ".join(str(value.get("governing_law") or "").split()).strip()
        if not re.fullmatch(r"[A-Z]{2}", country) or not governing_law:
            raise LegalTemplateError("template_jurisdiction_required")
        return {
            "country_code": country,
            "region": " ".join(str(value.get("region") or "").split()).strip()[:160],
            "governing_law": governing_law[:240],
            "owner_confirmed": bool(value.get("owner_confirmed")),
        }

    def _event(self, record: dict[str, Any], event_type: str, actor_id: str, detail: Mapping[str, Any]) -> None:
        events = record.setdefault("audit_events", [])
        previous_hash = events[-1]["event_hash"] if events else None
        event = {
            "sequence": len(events) + 1, "event_type": event_type,
            "occurred_at": _iso(self.clock()), "actor_id": str(actor_id or "unknown")[:160],
            "detail": deepcopy(dict(detail)), "previous_event_hash": previous_hash,
        }
        event["event_hash"] = sha256(_canonical(event)).hexdigest()
        events.append(event)

    def _public(self, record: dict[str, Any], *, include_content: bool = True) -> dict[str, Any]:
        result = deepcopy(record)
        if not include_content:
            result.pop("content", None)
        result["immutable_approved_version"] = bool(result.get("approval"))
        result["human_final_review_required"] = True
        return result

    def _load(self, workspace_id: str, template_id: str) -> dict[str, Any]:
        workspace = self._component(workspace_id, "workspace_id")
        template = self._component(template_id, "template_id")
        path = self.root / workspace / f"{template}.enc"
        if not path.exists():
            raise LegalTemplateError("template_not_found")
        return self.store.read(path, workspace_id=workspace, record_id=template)

    def _save(self, record: dict[str, Any]) -> None:
        path = self.root / record["workspace_id"] / f"{record['template_id']}.enc"
        ensure_workspace_record_write(
            workspace_folder=path.parent,
            record_path=path,
            record_patterns=("template-*.enc",),
            estimated_bytes=estimated_encrypted_record_bytes(record),
            error_type=LegalTemplateError,
        )
        self.store.write(path, record, workspace_id=record["workspace_id"], record_id=record["template_id"])

    @staticmethod
    def _component(value: str, field: str) -> str:
        clean = str(value or "").strip()
        if not clean or not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", clean):
            raise LegalTemplateError(f"invalid_{field}")
        return clean
