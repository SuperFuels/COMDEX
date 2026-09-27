"""Durable, workspace-isolated Legal matter intake and triage records."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import threading
from typing import Any, Callable, Mapping
from uuid import uuid4

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.legal_secure_storage import LegalEncryptedStore, LegalKeyStore
from backend.modules.aion_business.runtime.legal_record_governance import (
    LegalRecordGovernanceError,
    assert_deletable,
    destruction_receipt,
    governance_for,
    mark_exported,
    update_governance,
)
from backend.modules.aion_business.runtime.legal_resource_limits import (
    bounded_record_paths,
    ensure_workspace_record_write,
    estimated_encrypted_record_bytes,
)


class LegalMatterError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class LegalMatterService:
    SCHEMA_VERSION = "tessaris.legal-matter.v2"
    TYPES = {"CONTRACT", "COMPLAINT", "EMPLOYMENT", "PRIVACY", "DISPUTE", "GENERAL_ADVICE"}
    RISKS = {"LOW", "NORMAL", "HIGH", "URGENT"}
    STATUSES = {"OPEN", "ON_HOLD", "CLOSED"}
    LINK_TYPES = {"DOCUMENT", "COMMUNICATION", "SIGNATURE_ENVELOPE", "PROOF_RECEIPT"}
    OBLIGATION_TYPES = {"ACTION", "RENEWAL", "EXPIRY", "NOTICE", "REVIEW"}
    OBLIGATION_STATUSES = {"OPEN", "COMPLETED", "WAIVED"}
    ESCALATION_URGENCIES = {"NORMAL", "HIGH", "URGENT"}

    def __init__(
        self,
        root: str | Path | None = None,
        clock: Callable[[], datetime] = _utc_now,
        key_store: LegalKeyStore | None = None,
    ) -> None:
        self.root = Path(root) if root else AIONBusinessPaths.LEGAL_MATTERS
        self.clock = clock
        self._lock = threading.RLock()
        self.key_store = key_store or LegalKeyStore(self.root)
        self.store = LegalEncryptedStore(self.root, purpose="matter_records", key_store=self.key_store)
        self.destruction_store = LegalEncryptedStore(
            self.root, purpose="matter_destruction_receipts", key_store=self.key_store,
        )

    def list_matters(self, workspace_id: str) -> list[dict[str, Any]]:
        folder = self._workspace_dir(workspace_id)
        paths = bounded_record_paths(
            folder, ("matter-*.enc", "matter-*.json"), error_type=LegalMatterError,
        )
        records = [self._with_governance(self._read(path)) for path in paths]
        records.sort(key=lambda value: str(value.get("updated_at") or ""), reverse=True)
        return deepcopy(records)

    def get_matter(self, workspace_id: str, matter_id: str) -> dict[str, Any]:
        return deepcopy(self._with_governance(self._load(workspace_id, matter_id)))

    def create_matter(
        self,
        workspace_id: str,
        *,
        title: str,
        counterparty: str,
        matter_type: str,
        risk: str,
        summary: str,
        jurisdiction: Mapping[str, Any],
        actor_id: str,
    ) -> dict[str, Any]:
        clean_title = " ".join(str(title).split()).strip()
        if not clean_title:
            raise LegalMatterError("matter_title_required")
        clean_type = str(matter_type or "GENERAL_ADVICE").strip().upper().replace(" ", "_")
        clean_risk = str(risk or "NORMAL").strip().upper()
        if clean_type not in self.TYPES:
            raise LegalMatterError("unsupported_matter_type")
        if clean_risk not in self.RISKS:
            raise LegalMatterError("unsupported_matter_risk")
        legal_context = self._jurisdiction(jurisdiction)
        now = _iso(self.clock())
        matter_id = f"matter-{uuid4().hex}"
        record: dict[str, Any] = {
            "schema_version": self.SCHEMA_VERSION,
            "workspace_id": self._component(workspace_id, "workspace_id"),
            "matter_id": matter_id,
            "title": clean_title[:240],
            "counterparty": " ".join(str(counterparty).split()).strip()[:240],
            "matter_type": clean_type,
            "risk": clean_risk,
            "status": "OPEN",
            "summary": str(summary or "").strip()[:5000],
            "jurisdiction": legal_context,
            "created_at": now,
            "updated_at": now,
            "created_by": str(actor_id or "unknown")[:160],
            "linked_records": [],
            "obligations": [],
            "professional_escalations": [],
            "records_governance": governance_for({}),
            "audit_events": [],
        }
        self._event(record, "MATTER_CREATED", actor_id, {
            "matter_type": clean_type,
            "risk": clean_risk,
            "jurisdiction_confirmed": legal_context["owner_confirmed"],
        })
        self._save(record)
        return deepcopy(record)

    def triage_matter(
        self,
        workspace_id: str,
        matter_id: str,
        *,
        actor_id: str,
        risk: str | None = None,
        status: str | None = None,
        summary: str | None = None,
        jurisdiction: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, matter_id)
            changes: dict[str, Any] = {}
            if risk is not None:
                value = str(risk).strip().upper()
                if value not in self.RISKS:
                    raise LegalMatterError("unsupported_matter_risk")
                record["risk"] = value
                changes["risk"] = value
            if status is not None:
                value = str(status).strip().upper()
                if value not in self.STATUSES:
                    raise LegalMatterError("unsupported_matter_status")
                record["status"] = value
                changes["status"] = value
            if summary is not None:
                record["summary"] = str(summary).strip()[:5000]
                changes["summary_updated"] = True
            if jurisdiction is not None:
                record["jurisdiction"] = self._jurisdiction(jurisdiction)
                changes["jurisdiction_updated"] = True
            if not changes:
                raise LegalMatterError("triage_change_required")
            record["updated_at"] = _iso(self.clock())
            self._event(record, "MATTER_TRIAGED", actor_id, changes)
            self._save(record)
            return deepcopy(record)

    def link_record(
        self,
        workspace_id: str,
        matter_id: str,
        *,
        actor_id: str,
        record_type: str,
        reference_id: str,
        label: str = "",
        content_sha256: str = "",
    ) -> dict[str, Any]:
        """Link an existing protected record without copying its private content."""
        kind = str(record_type or "").strip().upper()
        if kind not in self.LINK_TYPES:
            raise LegalMatterError("unsupported_linked_record_type")
        reference = self._component(reference_id, "reference_id")
        digest = str(content_sha256 or "").strip().lower()
        if digest and (len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest)):
            raise LegalMatterError("linked_record_hash_invalid")
        with self._lock:
            record = self._load(workspace_id, matter_id)
            links = record.setdefault("linked_records", [])
            identity = (kind, reference)
            if any((item.get("record_type"), item.get("reference_id")) == identity for item in links):
                raise LegalMatterError("linked_record_already_exists")
            link = {
                "link_id": f"link-{uuid4().hex}",
                "record_type": kind,
                "reference_id": reference,
                "label": " ".join(str(label or "").split()).strip()[:240],
                "content_sha256": digest or None,
                "linked_at": _iso(self.clock()),
                "linked_by": str(actor_id or "unknown")[:160],
            }
            links.append(link)
            record["updated_at"] = _iso(self.clock())
            self._event(record, "MATTER_RECORD_LINKED", actor_id, {
                "link_id": link["link_id"], "record_type": kind,
                "reference_id": reference, "content_sha256": digest or None,
            })
            self._save(record)
            return deepcopy(record)

    def add_obligation(
        self,
        workspace_id: str,
        matter_id: str,
        *,
        actor_id: str,
        title: str,
        obligation_type: str,
        due_at: str,
        remind_at: list[str] | None = None,
        owner_id: str = "",
        source_reference_id: str = "",
    ) -> dict[str, Any]:
        clean_title = " ".join(str(title or "").split()).strip()
        if not clean_title:
            raise LegalMatterError("obligation_title_required")
        kind = str(obligation_type or "ACTION").strip().upper()
        if kind not in self.OBLIGATION_TYPES:
            raise LegalMatterError("unsupported_obligation_type")
        due = self._timestamp(due_at, "obligation_due_at")
        reminders = sorted({self._timestamp(value, "obligation_remind_at") for value in (remind_at or [])})
        if any(value >= due for value in reminders):
            raise LegalMatterError("obligation_reminder_must_precede_due_date")
        source = str(source_reference_id or "").strip()
        if source:
            source = self._component(source, "source_reference_id")
        with self._lock:
            record = self._load(workspace_id, matter_id)
            obligation = {
                "obligation_id": f"obligation-{uuid4().hex}",
                "title": clean_title[:240],
                "obligation_type": kind,
                "due_at": due,
                "remind_at": reminders,
                "owner_id": str(owner_id or "").strip()[:160],
                "source_reference_id": source or None,
                "status": "OPEN",
                "created_at": _iso(self.clock()),
                "created_by": str(actor_id or "unknown")[:160],
                "completed_at": None,
            }
            record.setdefault("obligations", []).append(obligation)
            record["updated_at"] = _iso(self.clock())
            self._event(record, "MATTER_OBLIGATION_CREATED", actor_id, {
                "obligation_id": obligation["obligation_id"], "obligation_type": kind,
                "due_at": due, "reminder_count": len(reminders),
            })
            self._save(record)
            return deepcopy(record)

    def update_obligation(
        self,
        workspace_id: str,
        matter_id: str,
        obligation_id: str,
        *,
        actor_id: str,
        status: str,
    ) -> dict[str, Any]:
        target = self._component(obligation_id, "obligation_id")
        value = str(status or "").strip().upper()
        if value not in self.OBLIGATION_STATUSES:
            raise LegalMatterError("unsupported_obligation_status")
        with self._lock:
            record = self._load(workspace_id, matter_id)
            obligation = next((item for item in record.setdefault("obligations", []) if item.get("obligation_id") == target), None)
            if obligation is None:
                raise LegalMatterError("obligation_not_found")
            obligation["status"] = value
            obligation["completed_at"] = _iso(self.clock()) if value in {"COMPLETED", "WAIVED"} else None
            record["updated_at"] = _iso(self.clock())
            self._event(record, "MATTER_OBLIGATION_STATUS_CHANGED", actor_id, {
                "obligation_id": target, "status": value,
            })
            self._save(record)
            return deepcopy(record)

    def due_obligations(self, workspace_id: str, *, as_of: str | None = None) -> list[dict[str, Any]]:
        cutoff = self._timestamp(as_of, "obligation_as_of") if as_of else _iso(self.clock())
        due: list[dict[str, Any]] = []
        for matter in self.list_matters(workspace_id):
            for obligation in matter.get("obligations") or []:
                if obligation.get("status") != "OPEN":
                    continue
                reminders = list(obligation.get("remind_at") or [])
                next_trigger = min([obligation["due_at"], *reminders])
                if next_trigger <= cutoff:
                    due.append({
                        **deepcopy(obligation),
                        "matter_id": matter["matter_id"],
                        "matter_title": matter["title"],
                        "risk": matter["risk"],
                        "overdue": obligation["due_at"] <= cutoff,
                    })
        due.sort(key=lambda item: (item["due_at"], item["matter_id"], item["obligation_id"]))
        return due

    def create_professional_escalation(
        self,
        workspace_id: str,
        matter_id: str,
        *,
        actor_id: str,
        reason: str,
        urgency: str,
        requested_professional: str = "",
    ) -> dict[str, Any]:
        clean_reason = str(reason or "").strip()
        if not clean_reason:
            raise LegalMatterError("professional_escalation_reason_required")
        level = str(urgency or "NORMAL").strip().upper()
        if level not in self.ESCALATION_URGENCIES:
            raise LegalMatterError("unsupported_professional_escalation_urgency")
        with self._lock:
            record = self._load(workspace_id, matter_id)
            escalation = {
                "escalation_id": f"escalation-{uuid4().hex}",
                "status": "DRAFT_REQUIRES_HUMAN_APPROVAL",
                "reason": clean_reason[:2000],
                "urgency": level,
                "requested_professional": " ".join(str(requested_professional or "").split()).strip()[:240],
                "created_at": _iso(self.clock()),
                "created_by": str(actor_id or "unknown")[:160],
                "matter_snapshot_sha256": sha256(_canonical({
                    "matter_id": record["matter_id"], "title": record["title"],
                    "risk": record["risk"], "jurisdiction": record["jurisdiction"],
                    "linked_record_ids": [item.get("reference_id") for item in record.get("linked_records") or []],
                })).hexdigest(),
                "external_delivery_authorized": False,
            }
            record.setdefault("professional_escalations", []).append(escalation)
            record["updated_at"] = _iso(self.clock())
            self._event(record, "PROFESSIONAL_ESCALATION_DRAFTED", actor_id, {
                "escalation_id": escalation["escalation_id"], "urgency": level,
                "external_delivery_authorized": False,
            })
            self._save(record)
            return deepcopy(record)

    def update_records_governance(
        self,
        workspace_id: str,
        matter_id: str,
        *,
        actor_id: str,
        retain_until: str | None = None,
        legal_hold: bool | None = None,
        legal_hold_reason: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, matter_id)
            try:
                _, changes = update_governance(
                    record, now=self.clock(), actor_id=actor_id, retain_until=retain_until,
                    legal_hold=legal_hold, legal_hold_reason=legal_hold_reason,
                )
            except LegalRecordGovernanceError as exc:
                raise LegalMatterError(str(exc)) from exc
            record["updated_at"] = _iso(self.clock())
            self._event(record, "RECORDS_GOVERNANCE_CHANGED", actor_id, changes)
            self._save(record)
            return deepcopy(record)

    def export_matter(self, workspace_id: str, matter_id: str, actor_id: str) -> tuple[str, bytes]:
        with self._lock:
            record = self._load(workspace_id, matter_id)
            self._event(record, "MATTER_EXPORTED", actor_id, {"format": "portable_json"})
            mark_exported(record, self.clock())
            record["updated_at"] = _iso(self.clock())
            self._save(record)
            body = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
            return f"{matter_id}.tessaris-legal-matter.json", body

    def destroy_matter(
        self,
        workspace_id: str,
        matter_id: str,
        *,
        actor_id: str,
        confirmation: str,
    ) -> dict[str, Any]:
        with self._lock:
            if str(confirmation or "").strip() != f"DELETE {matter_id}":
                raise LegalMatterError("exact_deletion_confirmation_required")
            record = self._load(workspace_id, matter_id)
            try:
                assert_deletable(record, now=self.clock(), terminal=record.get("status") == "CLOSED")
            except LegalRecordGovernanceError as exc:
                raise LegalMatterError(str(exc)) from exc
            receipt = destruction_receipt(
                record, record_type="legal_matter", record_id=matter_id,
                workspace_id=self._component(workspace_id, "workspace_id"),
                actor_id=actor_id, now=self.clock(),
            )
            receipt_path = self._destruction_path(workspace_id, str(receipt["receipt_id"]))
            self.destruction_store.write(
                receipt_path, receipt, workspace_id=workspace_id,
                record_id=str(receipt["receipt_id"]),
            )
            self._path(workspace_id, matter_id).unlink()
            legacy = self._legacy_path(workspace_id, matter_id)
            if legacy.exists():
                legacy.unlink()
            return deepcopy(receipt)

    def verify_audit_chain(self, workspace_id: str, matter_id: str) -> bool:
        record = self._load(workspace_id, matter_id)
        previous = "GENESIS"
        for event in record.get("audit_events") or []:
            body = {key: value for key, value in event.items() if key != "event_hash"}
            if body.get("previous_hash") != previous:
                return False
            current = sha256(_canonical(body)).hexdigest()
            if event.get("event_hash") != current:
                return False
            previous = current
        return True

    def _jurisdiction(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        country = str(raw.get("country_code") or "").strip().upper()
        governing = " ".join(str(raw.get("governing_law") or "").split()).strip()
        confirmed = bool(raw.get("owner_confirmed"))
        if len(country) != 2 or not country.isalpha():
            raise LegalMatterError("two_letter_jurisdiction_country_required")
        if not governing:
            raise LegalMatterError("governing_law_required")
        if not confirmed:
            raise LegalMatterError("jurisdiction_owner_confirmation_required")
        return {
            "country_code": country,
            "region": " ".join(str(raw.get("region") or "").split()).strip()[:160],
            "governing_law": governing[:240],
            "forum": " ".join(str(raw.get("forum") or "").split()).strip()[:240],
            "owner_confirmed": True,
            "confirmed_at": _iso(self.clock()),
            "notice": "Recorded business selection; not a legal determination by Tessaris.",
        }

    def _event(self, record: dict[str, Any], event_type: str, actor_id: str, detail: Mapping[str, Any]) -> None:
        events = record.setdefault("audit_events", [])
        body = {
            "event_id": f"evt-{uuid4().hex}",
            "event_type": event_type,
            "occurred_at": _iso(self.clock()),
            "actor_id": str(actor_id or "unknown")[:160],
            "detail": deepcopy(dict(detail)),
            "previous_hash": events[-1]["event_hash"] if events else "GENESIS",
        }
        events.append({**body, "event_hash": sha256(_canonical(body)).hexdigest()})

    def _workspace_dir(self, workspace_id: str) -> Path:
        workspace = self._component(workspace_id, "workspace_id")
        path = self.root / workspace
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(self, workspace_id: str, matter_id: str) -> Path:
        matter = self._component(matter_id, "matter_id")
        if not matter.startswith("matter-"):
            raise LegalMatterError("matter_not_found")
        return self._workspace_dir(workspace_id) / f"{matter}.enc"

    def _legacy_path(self, workspace_id: str, matter_id: str) -> Path:
        return self._path(workspace_id, matter_id).with_suffix(".json")

    def _destruction_path(self, workspace_id: str, receipt_id: str) -> Path:
        receipt = self._component(receipt_id, "receipt_id")
        folder = self._workspace_dir(workspace_id) / "_destruction"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{receipt}.enc"

    def _load(self, workspace_id: str, matter_id: str) -> dict[str, Any]:
        path = self._path(workspace_id, matter_id)
        if not path.exists():
            legacy = self._legacy_path(workspace_id, matter_id)
            if legacy.exists():
                record = self.store.migrate_plaintext(
                    legacy, path, workspace_id=workspace_id, record_id=matter_id,
                )
            else:
                raise LegalMatterError("matter_not_found")
        else:
            record = self._read(path)
        if record.get("workspace_id") != self._component(workspace_id, "workspace_id"):
            raise LegalMatterError("matter_not_found")
        return self._with_governance(record)

    @staticmethod
    def _with_governance(record: dict[str, Any]) -> dict[str, Any]:
        record.setdefault("linked_records", [])
        record.setdefault("obligations", [])
        record.setdefault("professional_escalations", [])
        record["records_governance"] = governance_for(record)
        return record

    @staticmethod
    def _timestamp(value: str | None, label: str) -> str:
        clean = str(value or "").strip()
        try:
            parsed = datetime.fromisoformat(clean.replace("Z", "+00:00"))
        except ValueError as exc:
            raise LegalMatterError(f"invalid_{label}") from exc
        if parsed.tzinfo is None:
            raise LegalMatterError(f"invalid_{label}")
        return _iso(parsed)

    @staticmethod
    def _component(value: str, label: str) -> str:
        clean = str(value or "").strip()
        if not clean or clean in {".", ".."} or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in clean):
            raise LegalMatterError(f"invalid_{label}")
        return clean

    def _read(self, path: Path) -> dict[str, Any]:
        workspace_id, record_id = path.parent.name, path.stem
        if path.suffix == ".json":
            encrypted = path.with_suffix(".enc")
            if encrypted.exists():
                return self.store.read(encrypted, workspace_id=workspace_id, record_id=record_id)
            return self.store.migrate_plaintext(
                path, encrypted, workspace_id=workspace_id, record_id=record_id,
            )
        return self.store.read(path, workspace_id=workspace_id, record_id=record_id)

    def _save(self, record: Mapping[str, Any]) -> None:
        path = self._path(str(record["workspace_id"]), str(record["matter_id"]))
        ensure_workspace_record_write(
            workspace_folder=path.parent,
            record_path=path,
            record_patterns=("matter-*.enc", "matter-*.json"),
            estimated_bytes=estimated_encrypted_record_bytes(record),
            error_type=LegalMatterError,
        )
        self.store.write(
            path, record,
            workspace_id=str(record["workspace_id"]), record_id=str(record["matter_id"]),
        )
