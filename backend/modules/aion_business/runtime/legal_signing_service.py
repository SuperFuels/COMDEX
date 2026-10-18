"""Persistent, approval-gated signing envelopes for the Legal workspace.

This deliberately does not reuse the old ``transactable_docs/dev`` prototype.
Every envelope binds signers to one immutable document version and every state
change is appended to a hash-chained audit trail.  Delivery is manual until an
approved messaging connector is configured.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
from html import escape
import io
import json
import os
from pathlib import Path
import re
import secrets
import threading
from typing import Any, Callable, Mapping
from uuid import uuid4
import zipfile

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.legal_document_proof import LegalDocumentProofService
from backend.modules.aion_business.runtime.legal_secure_storage import LegalEncryptedStore, LegalKeyStore
from backend.modules.aion_business.runtime.legal_record_governance import (
    LegalRecordGovernanceError,
    assert_deletable,
    destruction_receipt,
    governance_for,
    mark_exported,
    update_governance,
)
from backend.modules.aion_business.runtime.legal_delivery_service import (
    LegalDeliveryError,
    LegalDeliveryService,
)
from backend.modules.aion_business.runtime.legal_resource_limits import (
    bounded_record_paths,
    ensure_workspace_record_write,
    estimated_encrypted_record_bytes,
)


class LegalSigningError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


class LegalSigningService:
    SCHEMA_VERSION = "aion.legal-signing-envelope.v1"
    TERMINAL = {"COMPLETED", "DECLINED", "VOIDED", "EXPIRED"}
    SIGNER_VERIFICATION_METHODS = {"typed_name_email", "separate_channel_code"}
    SIGNER_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
    TOKEN_INDEX_WORKSPACE = "_public_signer_index"

    def __init__(
        self,
        root: str | Path | None = None,
        clock: Callable[[], datetime] = _utc_now,
        proof_service: LegalDocumentProofService | None = None,
        key_store: LegalKeyStore | None = None,
        delivery_service: LegalDeliveryService | None = None,
    ) -> None:
        self.root = Path(root) if root else AIONBusinessPaths.LEGAL_SIGNING
        self.clock = clock
        self._lock = threading.RLock()
        self.key_store = key_store or LegalKeyStore(self.root)
        self.store = LegalEncryptedStore(self.root, purpose="signing_records", key_store=self.key_store)
        self.token_index_root = self.root / "_signer_token_index"
        self.token_index_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.token_index_root, 0o700)
        self.token_index_store = LegalEncryptedStore(
            self.root, purpose="signing_token_index", key_store=self.key_store,
        )
        self.destruction_store = LegalEncryptedStore(
            self.root, purpose="signing_destruction_receipts", key_store=self.key_store,
        )
        self.proof_service = proof_service or LegalDocumentProofService(
            self.root, clock=clock, key_store=self.key_store,
        )
        self.delivery_service = delivery_service or LegalDeliveryService(
            self.root, clock=clock, key_store=self.key_store,
            senders={
                "resend": self._send_delivery_resend,
                "microsoft_graph": self._send_delivery_microsoft_graph,
            },
            receipt_checkers={
                "microsoft_graph": self._check_delivery_microsoft_graph,
            },
        )

    def list_envelopes(self, workspace_id: str) -> list[dict[str, Any]]:
        folder = self._workspace_dir(workspace_id)
        paths = bounded_record_paths(
            folder, ("*.enc", "*.json"), error_type=LegalSigningError,
        )
        items = [self._refresh_expiry(self._with_governance(self._read(path))) for path in paths]
        items.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return [self._public(item) for item in items]

    def get_envelope(self, workspace_id: str, envelope_id: str) -> dict[str, Any]:
        record = self._refresh_expiry(self._load(workspace_id, envelope_id))
        return self._public(record)

    def create_envelope(
        self,
        workspace_id: str,
        *,
        title: str,
        document_content: str,
        signers: list[Mapping[str, Any]],
        actor_id: str,
        expires_in_days: int = 14,
        supersedes_envelope_id: str | None = None,
    ) -> dict[str, Any]:
        title = " ".join(str(title).split()).strip()
        content = str(document_content).strip()
        if not title or not content:
            raise LegalSigningError("title_and_document_content_required")
        if len(content.encode("utf-8")) > 1_000_000:
            raise LegalSigningError("document_content_too_large")
        if not signers or len(signers) > 20:
            raise LegalSigningError("one_to_twenty_signers_required")
        normalized: list[dict[str, Any]] = []
        seen_emails: set[str] = set()
        for index, raw in enumerate(signers, start=1):
            name = " ".join(str(raw.get("name") or "").split()).strip()
            email = str(raw.get("email") or "").strip().lower()
            role = " ".join(str(raw.get("role") or "Signer").split()).strip()[:100]
            verification_method = str(raw.get("verification_method") or "typed_name_email").strip().lower()
            if not name or "@" not in email or email in seen_emails:
                raise LegalSigningError("each_signer_requires_a_unique_name_and_email")
            if verification_method not in self.SIGNER_VERIFICATION_METHODS:
                raise LegalSigningError("unsupported_signer_verification_method")
            seen_emails.add(email)
            normalized.append({
                "signer_id": f"signer-{uuid4().hex}", "name": name[:160], "email": email[:254],
                "role": role, "order": index, "status": "PENDING", "signed_at": None,
                "declined_at": None, "accepted_document_hash": None, "signature_method": None,
                "token_hash": None, "token_created_at": None,
                "verification_method": verification_method,
                "verification_code_hash": None, "verification_code_created_at": None,
            })
        now = self.clock()
        days = max(1, min(int(expires_in_days), 90))
        envelope_id = f"env-{uuid4().hex}"
        document = {
            "document_id": f"doc-{uuid4().hex}", "version": 1, "title": title,
            "content": content, "content_hash": sha256(content.encode("utf-8")).hexdigest(),
            "locked_at": _iso(now),
        }
        predecessor: dict[str, Any] | None = None
        if str(supersedes_envelope_id or "").strip():
            predecessor = self._load(workspace_id, str(supersedes_envelope_id).strip())
            self._require_status(predecessor, {"COMPLETED"})
            predecessor_lifecycle = dict(predecessor.get("lifecycle") or {})
            if predecessor_lifecycle.get("superseded_by_envelope_id"):
                raise LegalSigningError("document_already_superseded")

        record: dict[str, Any] = {
            "schema_version": self.SCHEMA_VERSION, "workspace_id": workspace_id,
            "envelope_id": envelope_id, "title": title, "status": "DRAFT",
            "created_at": _iso(now), "updated_at": _iso(now),
            "expires_at": _iso(now + timedelta(days=days)), "document": document,
            "signers": normalized,
            "approval": {"required": True, "status": "NOT_SUBMITTED", "submitted_at": None,
                         "approved_at": None, "approved_by": None, "review_hash": None},
            "delivery": {"mode": "manual_secure_link", "provider_configured": False,
                         "external_delivery_enabled": False, "issued_at": None,
                         "reminders": [], "signed_copy_delivery": []},
            "lifecycle": {
                "status": "DRAFT",
                "supersedes_envelope_id": predecessor.get("envelope_id") if predecessor else None,
                "supersedes_manifest_hash": (predecessor.get("signed_copy") or {}).get("manifest_hash") if predecessor else None,
                "superseded_by_envelope_id": None,
                "effective_at": None,
                "notices": [],
            },
            "records_governance": governance_for({}),
            "audit_events": [], "signed_copy": None,
        }
        self._event(record, "ENVELOPE_CREATED", actor_id, {"document_hash": document["content_hash"], "signer_count": len(normalized)})
        if predecessor:
            self._event(record, "REPLACEMENT_DRAFT_CREATED", actor_id, {
                "supersedes_envelope_id": predecessor["envelope_id"],
                "supersedes_manifest_hash": (predecessor.get("signed_copy") or {}).get("manifest_hash"),
            })
        self._save(record)
        return self._public(record)

    def submit_for_approval(self, workspace_id: str, envelope_id: str, actor_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, envelope_id)
            self._require_status(record, {"DRAFT"})
            record["status"] = "PENDING_APPROVAL"
            record["approval"].update({"status": "PENDING", "submitted_at": _iso(self.clock())})
            review = {"envelope_id": record["envelope_id"], "document_hash": record["document"]["content_hash"],
                      "signers": [{"name": s["name"], "email": s["email"], "order": s["order"],
                                   "verification_method": s.get("verification_method", "typed_name_email")}
                                  for s in record["signers"]],
                      "expires_at": record["expires_at"]}
            record["approval"]["review_hash"] = _digest(review)
            self._event(record, "APPROVAL_REQUESTED", actor_id, {"review_hash": record["approval"]["review_hash"]})
            self._save(record)
            return self._public(record)

    def approve(self, workspace_id: str, envelope_id: str, actor_id: str, review_hash: str) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, envelope_id)
            self._require_status(record, {"PENDING_APPROVAL"})
            expected = str(record["approval"].get("review_hash") or "")
            if not expected or not hmac.compare_digest(expected, str(review_hash or "")):
                raise LegalSigningError("approval_review_hash_changed")
            record["status"] = "APPROVED"
            record["approval"].update({"status": "APPROVED", "approved_at": _iso(self.clock()), "approved_by": actor_id})
            self._event(record, "ENVELOPE_APPROVED", actor_id, {"review_hash": expected})
            self._save(record)
            return self._public(record)

    def issue(self, workspace_id: str, envelope_id: str, actor_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, envelope_id)
            self._require_status(record, {"APPROVED"})
            links: list[dict[str, str]] = []
            for signer in record["signers"]:
                links.append(self._rotate_signer_credentials(signer))
            record["status"] = "ISSUED"
            record["delivery"]["issued_at"] = _iso(self.clock())
            self._event(record, "SECURE_LINKS_ISSUED", actor_id, {"delivery_mode": "manual_secure_link", "signer_count": len(links)})
            self._save(record)
            response = self._public(record)
            response["secure_links"] = links  # tokens are returned once and never stored in plaintext
            return response

    def signer_view(self, token: str) -> dict[str, Any]:
        record, signer = self._find_by_token(token)
        record = self._refresh_expiry(record)
        if record["status"] in {"VOIDED", "EXPIRED", "DECLINED"}:
            raise LegalSigningError(f"envelope_{record['status'].lower()}")
        current = self._current_signer(record)
        can_sign = bool(current and current["signer_id"] == signer["signer_id"] and signer["status"] == "PENDING")
        return {"envelope_id": record["envelope_id"], "title": record["title"], "status": record["status"],
                "expires_at": record["expires_at"], "document": deepcopy(record["document"]),
                "signer": {key: signer.get(key) for key in ("signer_id", "name", "email", "role", "order", "status", "verification_method")},
                "can_sign": can_sign, "signing_order_enforced": True}

    def sign(self, token: str, typed_name: str, identity_email: str, identity_code: str = "") -> dict[str, Any]:
        with self._lock:
            record, signer = self._find_by_token(token)
            record = self._refresh_expiry(record)
            self._require_status(record, {"ISSUED", "IN_PROGRESS"})
            current = self._current_signer(record)
            if not current or current["signer_id"] != signer["signer_id"]:
                raise LegalSigningError("signing_order_not_reached")
            if signer["status"] != "PENDING":
                raise LegalSigningError("signer_already_completed")
            if str(identity_email).strip().lower() != signer["email"] or " ".join(str(typed_name).split()).casefold() != signer["name"].casefold():
                raise LegalSigningError("signer_identity_did_not_match")
            verification_method = str(signer.get("verification_method") or "typed_name_email")
            signature_method = "typed_name_plus_email_match"
            if verification_method == "separate_channel_code":
                expected = str(signer.get("verification_code_hash") or "")
                supplied = self._verification_code_hash(identity_code)
                if not expected or not hmac.compare_digest(expected, supplied):
                    raise LegalSigningError("separate_channel_verification_code_did_not_match")
                signature_method = "typed_name_email_plus_separate_channel_code"
            self._delete_token_index(str(signer.get("token_hash") or ""))
            signer.update({"status": "SIGNED", "signed_at": _iso(self.clock()), "signature_method": signature_method,
                           "accepted_document_hash": record["document"]["content_hash"],
                           "token_hash": None, "verification_code_hash": None})
            self._event(record, "DOCUMENT_SIGNED", f"signer:{signer['signer_id']}", {
                "signer_id": signer["signer_id"], "document_hash": signer["accepted_document_hash"],
                "verification_method": verification_method,
            })
            if all(item["status"] == "SIGNED" for item in record["signers"]):
                record["status"] = "COMPLETED"
                manifest = {"envelope_id": record["envelope_id"], "document_hash": record["document"]["content_hash"],
                            "completed_at": _iso(self.clock()), "signatures": [{"signer_id": item["signer_id"], "name": item["name"], "email": item["email"], "signed_at": item["signed_at"], "method": item["signature_method"]} for item in record["signers"]]}
                record["signed_copy"] = {**manifest, "manifest_hash": _digest(manifest), "delivery_status": "READY_FOR_APPROVED_DELIVERY"}
                self._event(record, "SIGNED_COPY_SEALED", "system", {"manifest_hash": record["signed_copy"]["manifest_hash"]})
                self._activate_lifecycle(record)
                try:
                    proof = self.proof_service.create_for_envelope(record)
                    chain = dict(proof.get("glyphchain") or {})
                    record["glyphchain_proof"] = {
                        "proof_id": (proof.get("glyphchain_payload") or {}).get("proof_id"),
                        "status": chain.get("status"),
                        "tx_id": chain.get("tx_id"),
                        "tx_hash": chain.get("tx_hash"),
                        "block_height": chain.get("block_height"),
                        "requires_photon": False,
                        "moves_currency": False,
                    }
                except Exception as exc:
                    record["glyphchain_proof"] = {
                        "status": "PROOF_PREPARATION_FAILED_RETRY_AVAILABLE",
                        "error": str(exc)[:500],
                        "requires_photon": False,
                        "moves_currency": False,
                    }
            else:
                record["status"] = "IN_PROGRESS"
            self._save(record)
            return self._public(record)

    def record_lifecycle_notice(
        self,
        workspace_id: str,
        envelope_id: str,
        actor_id: str,
        *,
        notice_type: str,
        reason: str,
        effective_at: str,
        reference: str = "",
        acknowledge_preserved_evidence: bool = False,
    ) -> dict[str, Any]:
        """Record a non-destructive post-completion lifecycle notice.

        A notice never deletes or rewrites the completed document or its proof.
        It records the business assertion and preserves the earlier evidence.
        """
        with self._lock:
            record = self._load(workspace_id, envelope_id)
            self._require_status(record, {"COMPLETED"})
            kind = str(notice_type or "").strip().upper()
            if kind not in {"TERMINATED", "RESCINDED", "REVOKED_BY_ISSUER"}:
                raise LegalSigningError("unsupported_lifecycle_notice")
            if not acknowledge_preserved_evidence:
                raise LegalSigningError("preserved_evidence_acknowledgement_required")
            clean_reason = " ".join(str(reason or "").split()).strip()[:1000]
            clean_effective = str(effective_at or "").strip()[:40]
            if not clean_reason or not clean_effective:
                raise LegalSigningError("lifecycle_reason_and_effective_at_required")
            lifecycle = record.setdefault("lifecycle", {
                "status": "ACTIVE", "supersedes_envelope_id": None,
                "supersedes_manifest_hash": None, "superseded_by_envelope_id": None,
                "effective_at": record.get("signed_copy", {}).get("completed_at"), "notices": [],
            })
            notice = {
                "notice_id": f"notice-{uuid4().hex}",
                "type": kind,
                "reason": clean_reason,
                "effective_at": clean_effective,
                "recorded_at": _iso(self.clock()),
                "recorded_by": actor_id,
                "reference": " ".join(str(reference or "").split()).strip()[:240] or None,
                "preserves_original_evidence": True,
            }
            lifecycle.setdefault("notices", []).append(notice)
            lifecycle["status"] = kind
            self._event(record, f"DOCUMENT_{kind}", actor_id, notice)
            self._save(record)
            return self._public(record)

    def document_history(self, workspace_id: str, envelope_id: str) -> dict[str, Any]:
        """Return and verify the linked predecessor history for one document."""
        current = self._load(workspace_id, envelope_id)
        chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        while current:
            current_id = str(current.get("envelope_id") or "")
            if not current_id or current_id in seen:
                raise LegalSigningError("document_history_cycle_detected")
            seen.add(current_id)
            proof_verification = None
            if current.get("status") == "COMPLETED":
                try:
                    proof_verification = self.verify_document_proof(workspace_id, current_id)
                except Exception as exc:
                    proof_verification = {"valid": False, "errors": [str(exc)]}
            chain.append({
                "envelope_id": current_id,
                "title": current.get("title"),
                "status": current.get("status"),
                "document_hash": (current.get("document") or {}).get("content_hash"),
                "manifest_hash": (current.get("signed_copy") or {}).get("manifest_hash"),
                "lifecycle": deepcopy(current.get("lifecycle") or {}),
                "audit_chain_valid": self.verify_audit_chain(workspace_id, current_id),
                "proof_verification": proof_verification,
            })
            predecessor_id = str((current.get("lifecycle") or {}).get("supersedes_envelope_id") or "")
            current = self._load(workspace_id, predecessor_id) if predecessor_id else None
        links_valid = all(
            chain[index]["lifecycle"].get("supersedes_manifest_hash") == chain[index + 1]["manifest_hash"]
            for index in range(len(chain) - 1)
        )
        return {
            "schema_version": "tessaris.legal-document-history.v1",
            "workspace_id": workspace_id,
            "requested_envelope_id": envelope_id,
            "newest_to_oldest": chain,
            "history_links_valid": links_valid,
            "all_audit_chains_valid": all(item["audit_chain_valid"] for item in chain),
            "all_available_proofs_valid": all(
                item["proof_verification"] is None or item["proof_verification"].get("valid") is True
                for item in chain
            ),
        }

    def decline(self, token: str, reason: str) -> dict[str, Any]:
        with self._lock:
            record, signer = self._find_by_token(token)
            record = self._refresh_expiry(record)
            self._require_status(record, {"ISSUED", "IN_PROGRESS"})
            self._delete_token_index(str(signer.get("token_hash") or ""))
            signer.update({
                "status": "DECLINED", "declined_at": _iso(self.clock()),
                "token_hash": None, "verification_code_hash": None,
            })
            record["status"] = "DECLINED"
            self._event(record, "SIGNER_DECLINED", f"signer:{signer['signer_id']}", {"signer_id": signer["signer_id"], "reason": str(reason)[:500]})
            self._save(record)
            return self._public(record)

    def void(self, workspace_id: str, envelope_id: str, actor_id: str, reason: str) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, envelope_id)
            if record["status"] in self.TERMINAL:
                raise LegalSigningError("completed_or_terminal_envelope_cannot_be_voided")
            self._deactivate_record_tokens(record)
            record["status"] = "VOIDED"
            self._event(record, "ENVELOPE_VOIDED", actor_id, {"reason": str(reason)[:500]})
            self._save(record)
            return self._public(record)

    def record_reminder(self, workspace_id: str, envelope_id: str, actor_id: str, signer_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._refresh_expiry(self._load(workspace_id, envelope_id))
            self._require_status(record, {"ISSUED", "IN_PROGRESS"})
            signer = next((item for item in record["signers"] if item["signer_id"] == signer_id), None)
            if not signer or signer["status"] != "PENDING":
                raise LegalSigningError("pending_signer_not_found")
            secure_link = self._rotate_signer_credentials(signer)
            reminder = {"reminder_id": f"rem-{uuid4().hex}", "signer_id": signer_id, "created_at": _iso(self.clock()),
                        "delivery_status": "LINK_ROTATED_NOT_SENT_CHANNEL_NOT_CONFIGURED"}
            record["delivery"]["reminders"].append(reminder)
            self._event(record, "REMINDER_PREPARED", actor_id, reminder)
            self._save(record)
            response = self._public(record)
            response["secure_link"] = secure_link
            return response

    def verify_audit_chain(self, workspace_id: str, envelope_id: str) -> bool:
        record = self._load(workspace_id, envelope_id)
        previous = "GENESIS"
        for event in record.get("audit_events") or []:
            core = {key: event[key] for key in ("sequence", "event_id", "event_type", "actor_id", "occurred_at", "payload_hash", "previous_hash")}
            if event["previous_hash"] != previous or not hmac.compare_digest(event["event_hash"], _digest(core)):
                return False
            previous = event["event_hash"]
        return True

    def update_records_governance(
        self,
        workspace_id: str,
        envelope_id: str,
        *,
        actor_id: str,
        retain_until: str | None = None,
        legal_hold: bool | None = None,
        legal_hold_reason: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, envelope_id)
            try:
                _, changes = update_governance(
                    record, now=self.clock(), actor_id=actor_id, retain_until=retain_until,
                    legal_hold=legal_hold, legal_hold_reason=legal_hold_reason,
                )
            except LegalRecordGovernanceError as exc:
                raise LegalSigningError(str(exc)) from exc
            self._event(record, "RECORDS_GOVERNANCE_CHANGED", actor_id, changes)
            self._save(record)
            return self._public(record)

    def destroy_envelope(
        self,
        workspace_id: str,
        envelope_id: str,
        *,
        actor_id: str,
        confirmation: str,
    ) -> dict[str, Any]:
        with self._lock:
            if str(confirmation or "").strip() != f"DELETE {envelope_id}":
                raise LegalSigningError("exact_deletion_confirmation_required")
            record = self._load(workspace_id, envelope_id)
            try:
                assert_deletable(
                    record, now=self.clock(), terminal=record.get("status") in self.TERMINAL,
                )
            except LegalRecordGovernanceError as exc:
                raise LegalSigningError(str(exc)) from exc
            receipt = destruction_receipt(
                record, record_type="signature_envelope", record_id=envelope_id,
                workspace_id=workspace_id, actor_id=actor_id, now=self.clock(),
            )
            receipt.update({
                "document_sha256": (record.get("document") or {}).get("content_hash"),
                "signed_copy_manifest_sha256": (record.get("signed_copy") or {}).get("manifest_hash"),
                "glyphchain_proof_id": (record.get("glyphchain_proof") or {}).get("proof_id"),
            })
            receipt_path = self._destruction_path(workspace_id, str(receipt["receipt_id"]))
            self.destruction_store.write(
                receipt_path, receipt, workspace_id=workspace_id,
                record_id=str(receipt["receipt_id"]),
            )
            self._path(workspace_id, envelope_id).unlink()
            legacy = self._legacy_path(workspace_id, envelope_id)
            if legacy.exists():
                legacy.unlink()
            return deepcopy(receipt)

    def record_signed_copy_delivery(self, workspace_id: str, envelope_id: str, actor_id: str, signer_id: str, delivery_reference: str) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, envelope_id)
            self._require_status(record, {"COMPLETED"})
            signer = next((item for item in record["signers"] if item["signer_id"] == signer_id), None)
            reference = " ".join(str(delivery_reference).split()).strip()[:240]
            if not signer or not reference:
                raise LegalSigningError("signer_and_delivery_reference_required")
            delivery = {"delivery_id": f"delivery-{uuid4().hex}", "signer_id": signer_id,
                        "recipient_email": signer["email"], "method": "manual_confirmed_delivery",
                        "delivery_reference": reference, "delivered_at": _iso(self.clock()),
                        "manifest_hash": record["signed_copy"]["manifest_hash"]}
            record["delivery"]["signed_copy_delivery"].append(delivery)
            self._event(record, "SIGNED_COPY_DELIVERY_RECORDED", actor_id, delivery)
            self._save(record)
            return self._public(record)

    def queue_signed_copy_deliveries(
        self,
        workspace_id: str,
        envelope_id: str,
        *,
        actor_id: str,
        provider: str,
        acknowledge_external_send: bool,
    ) -> dict[str, Any]:
        with self._lock:
            if not acknowledge_external_send:
                raise LegalSigningError("external_send_acknowledgement_required")
            record = self._load(workspace_id, envelope_id)
            self._require_status(record, {"COMPLETED"})
            existing = self.delivery_service.status(workspace_id, envelope_id)
            if existing["items"]:
                providers = {str(item.get("provider") or "") for item in existing["items"]}
                if providers != {str(provider or "").strip().lower()}:
                    raise LegalSigningError("signed_copy_delivery_provider_already_selected")
                if len(existing["items"]) != len(record["signers"]):
                    raise LegalSigningError("signed_copy_delivery_outbox_incomplete")
                return existing
            filename, package = self.build_evidence_package(workspace_id, envelope_id, actor_id)
            record = self._load(workspace_id, envelope_id)
            queued = []
            for signer in record["signers"]:
                try:
                    queued.append(self.delivery_service.queue(
                        workspace_id,
                        envelope_id=envelope_id,
                        manifest_hash=str((record.get("signed_copy") or {}).get("manifest_hash") or ""),
                        signer=signer,
                        provider=provider,
                        subject=f"Completed signed document · {record['title']}",
                        body_text=(
                            f"The completed signed document '{record['title']}' is attached with its "
                            "Tessaris integrity evidence. Keep this private evidence package secure."
                        ),
                        attachment_name=filename,
                        attachment_bytes=package,
                        approved_by=actor_id,
                        acknowledge_external_send=acknowledge_external_send,
                    ))
                except LegalDeliveryError as exc:
                    raise LegalSigningError(str(exc)) from exc
            record["delivery"]["mode"] = "approved_connector_outbox"
            record["delivery"]["provider_configured"] = self._delivery_provider_configured(provider)
            record["delivery"]["external_delivery_enabled"] = True
            record["delivery"]["delivery_authorized_at"] = _iso(self.clock())
            record["delivery"]["outbox_delivery_ids"] = [item["delivery_id"] for item in queued]
            self._event(record, "SIGNED_COPY_DELIVERIES_QUEUED", actor_id, {
                "provider": provider, "required_party_count": len(queued),
            })
            self._save(record)
            return self.delivery_service.status(workspace_id, envelope_id)

    def send_queued_signed_copies(
        self,
        workspace_id: str,
        *,
        actor_id: str,
        acknowledge_external_send: bool,
        limit: int = 25,
        force: bool = False,
    ) -> dict[str, Any]:
        try:
            return self.delivery_service.deliver_due(
                workspace_id, actor_id=actor_id,
                acknowledge_external_send=acknowledge_external_send,
                limit=limit, force=force,
            )
        except LegalDeliveryError as exc:
            raise LegalSigningError(str(exc)) from exc

    def confirm_signed_copy_delivery(
        self,
        workspace_id: str,
        delivery_id: str,
        *,
        actor_id: str,
        outcome: str,
        provider_reference: str,
    ) -> dict[str, Any]:
        try:
            delivery = self.delivery_service.confirm(
                workspace_id, delivery_id, outcome=outcome,
                provider_reference=provider_reference, actor_id=actor_id,
            )
        except LegalDeliveryError as exc:
            raise LegalSigningError(str(exc)) from exc
        if delivery["status"] == "DELIVERED":
            record = self._load(workspace_id, str(delivery["envelope_id"]))
            already = any(
                item.get("signer_id") == delivery["signer_id"]
                for item in (record.get("delivery") or {}).get("signed_copy_delivery") or []
            )
            if not already:
                self.record_signed_copy_delivery(
                    workspace_id, str(delivery["envelope_id"]), actor_id,
                    str(delivery["signer_id"]), provider_reference,
                )
        return {
            "delivery": delivery,
            "outbox": self.delivery_service.status(workspace_id, str(delivery["envelope_id"])),
        }

    def retry_signed_copy_delivery(
        self,
        workspace_id: str,
        delivery_id: str,
        *,
        actor_id: str,
        reason: str,
        acknowledge_external_send: bool,
    ) -> dict[str, Any]:
        try:
            return self.delivery_service.retry_or_resend(
                workspace_id, delivery_id, actor_id=actor_id, reason=reason,
                acknowledge_external_send=acknowledge_external_send,
            )
        except LegalDeliveryError as exc:
            raise LegalSigningError(str(exc)) from exc

    def ingest_resend_delivery_webhook(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        *,
        webhook_secrets: str | list[str],
    ) -> dict[str, Any]:
        """Apply one authenticated Resend callback and synchronize the envelope.

        The public route returns only a bounded acknowledgement, while this service
        is allowed to use the encrypted provider index to find the owning workspace.
        """

        try:
            result = self.delivery_service.ingest_resend_webhook(
                raw_body, headers, webhook_secrets=webhook_secrets,
            )
        except LegalDeliveryError as exc:
            raise LegalSigningError(str(exc)) from exc
        if result.get("ignored") or result.get("duplicate") or result.get("outcome") != "DELIVERED":
            return result
        workspace_id = str(result.get("workspace_id") or "")
        delivery_id = str(result.get("delivery_id") or "")
        delivery = self.delivery_service._load(workspace_id, delivery_id)
        record = self._load(workspace_id, str(delivery["envelope_id"]))
        already = any(
            item.get("signer_id") == delivery["signer_id"]
            for item in (record.get("delivery") or {}).get("signed_copy_delivery") or []
        )
        if not already:
            self.record_signed_copy_delivery(
                workspace_id, str(delivery["envelope_id"]), "resend_webhook",
                str(delivery["signer_id"]), str(delivery["confirmation_reference"]),
            )
        return result

    def signed_copy_delivery_status(self, workspace_id: str, envelope_id: str | None = None) -> dict[str, Any]:
        return self.delivery_service.status(workspace_id, envelope_id)

    def refresh_microsoft_graph_delivery_receipts(
        self,
        workspace_id: str,
        *,
        actor_id: str,
        limit: int = 25,
    ) -> dict[str, Any]:
        try:
            result = self.delivery_service.refresh_provider_receipts(
                workspace_id,
                provider="microsoft_graph",
                actor_id=actor_id,
                limit=limit,
            )
        except LegalDeliveryError as exc:
            raise LegalSigningError(str(exc)) from exc
        for delivery in result.get("items") or []:
            if delivery.get("status") != "DELIVERED":
                continue
            record = self._load(workspace_id, str(delivery["envelope_id"]))
            already = any(
                item.get("signer_id") == delivery.get("signer_id")
                for item in (record.get("delivery") or {}).get("signed_copy_delivery") or []
            )
            if not already:
                self.record_signed_copy_delivery(
                    workspace_id,
                    str(delivery["envelope_id"]),
                    actor_id,
                    str(delivery["signer_id"]),
                    str(delivery.get("confirmation_reference") or "microsoft_graph_message_trace"),
                )
        return result

    @staticmethod
    def _delivery_provider_configured(provider: str) -> bool:
        provider = str(provider or "").strip().lower()
        if provider == "resend":
            return bool(os.getenv("RESEND_API_KEY") and (os.getenv("RESEND_FROM_EMAIL") or os.getenv("DEFAULT_FROM_EMAIL")))
        if provider == "microsoft_graph":
            return bool(os.getenv("MICROSOFT_GRAPH_ACCESS_TOKEN"))
        return False

    def document_proof(self, workspace_id: str, envelope_id: str) -> dict[str, Any]:
        self._require_status(self._load(workspace_id, envelope_id), {"COMPLETED"})
        record = self._load(workspace_id, envelope_id)
        return self.proof_service.bundle_for_envelope(workspace_id, envelope_id)

    def submit_document_proof(self, workspace_id: str, envelope_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._load(workspace_id, envelope_id)
            self._require_status(record, {"COMPLETED"})
            try:
                bundle = self.proof_service.bundle_for_envelope(workspace_id, envelope_id)
            except Exception:
                bundle = self.proof_service.create_for_envelope(record)
            bundle = self.proof_service.submit_pending(record, bundle=bundle)
            chain = dict(bundle.get("glyphchain") or {})
            record["glyphchain_proof"] = {
                "proof_id": (bundle.get("glyphchain_payload") or {}).get("proof_id"),
                "status": chain.get("status"),
                "tx_id": chain.get("tx_id"),
                "tx_hash": chain.get("tx_hash"),
                "block_height": chain.get("block_height"),
                "requires_photon": False,
                "moves_currency": False,
            }
            self._save(record)
            return bundle

    def verify_document_proof(
        self,
        workspace_id: str,
        envelope_id: str,
        document_content: str | None = None,
        trusted_validator_set_root: str | None = None,
    ) -> dict[str, Any]:
        record = self._load(workspace_id, envelope_id)
        self._require_status(record, {"COMPLETED"})
        bundle = self.proof_service.bundle_for_envelope(workspace_id, envelope_id)
        return self.proof_service.verify_bundle(
            bundle,
            document_content=document_content,
            private_signers=list(record.get("signers") or []),
            trusted_validator_set_root=trusted_validator_set_root,
        )

    def proof_outbox_status(self, workspace_id: str) -> dict[str, Any]:
        status = self.proof_service.outbox_status()
        items = [item for item in status["items"] if item.get("workspace_id") == workspace_id]
        counts: dict[str, int] = {}
        for item in items:
            value = str(item.get("status") or "UNKNOWN")
            counts[value] = counts.get(value, 0) + 1
        return {"counts": counts, "items": items}

    def retry_document_proofs(self, workspace_id: str, *, limit: int = 25) -> dict[str, Any]:
        return self.proof_service.retry_due(limit=limit, force=True, workspace_id=workspace_id)

    def build_evidence_package(
        self, workspace_id: str, envelope_id: str, actor_id: str = "workspace_user",
    ) -> tuple[str, bytes]:
        """Create a self-contained private evidence package for the parties.

        The archive is generated in memory and is never placed on GlyphChain.
        It contains the exact frozen text, signatures manifest, hash-chained
        audit events and portable commitment-only receipt.
        """
        record = self._load(workspace_id, envelope_id)
        self._require_status(record, {"COMPLETED"})
        self._event(record, "EVIDENCE_PACKAGE_EXPORTED", actor_id, {"format": "tessaris-evidence.zip"})
        mark_exported(record, self.clock())
        self._save(record)
        proof = self.proof_service.bundle_for_envelope(workspace_id, envelope_id)
        history = self.document_history(workspace_id, envelope_id)
        certificate = {
            "schema_version": "tessaris.legal-evidence-certificate.v1",
            "assurance": "tamper-evident electronic signing and document-integrity proof",
            "not_a_claim_of": [
                "qualified electronic signature",
                "qualified electronic seal",
                "qualified trust service",
            ],
            "workspace_id": workspace_id,
            "envelope_id": envelope_id,
            "title": record["title"],
            "document": {
                "document_id": record["document"]["document_id"],
                "version": record["document"]["version"],
                "sha256": record["document"]["content_hash"],
                "locked_at": record["document"]["locked_at"],
            },
            "completion": deepcopy(record["signed_copy"]),
            "lifecycle": deepcopy(record.get("lifecycle") or {}),
            "signers": [
                {
                    key: signer.get(key)
                    for key in (
                        "signer_id", "name", "email", "role", "order", "status",
                        "signed_at", "signature_method", "accepted_document_hash",
                    )
                }
                for signer in record["signers"]
            ],
            "private_commitment_verification": {
                "signatures_root": (proof.get("glyphchain_payload") or {}).get("signatures_root"),
                "instruction": "The local verifier can recompute this root from the private signer records in this certificate; names and email addresses are not placed on GlyphChain.",
            },
            "audit_chain_valid_at_export": self.verify_audit_chain(workspace_id, envelope_id),
            "glyphchain": {
                "proof_id": (proof.get("glyphchain_payload") or {}).get("proof_id"),
                **deepcopy(dict(proof.get("glyphchain") or {})),
            },
            "verification_instructions": {
                "verifier": "Tessaris GlyphChain Proof Verifier",
                "document_file": "document.txt",
                "proof_file": f"{envelope_id}.tessaris-proof",
                "privacy": "verification may be performed locally without uploading the document",
            },
            "exported_at": _iso(self.clock()),
        }
        readme = (
            "TESSARIS LEGAL EVIDENCE PACKAGE\n\n"
            "This archive contains the frozen document, signing manifest, audit history and "
            "GlyphChain proof receipt. Open the local Tessaris GlyphChain Proof Verifier, select "
            "document.txt and the .tessaris-proof file, then choose Verify locally.\n\n"
            "A successful integrity check does not determine whether the agreement is lawful, "
            "fair or enforceable and is not a claim of qualified electronic signature status.\n"
        )
        signed_document = self._render_signed_document(record, proof)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("README.txt", readme)
            archive.writestr("document.txt", str(record["document"]["content"]))
            archive.writestr("signed-document.html", signed_document)
            archive.writestr(
                f"{envelope_id}.tessaris-proof",
                json.dumps(proof, indent=2, sort_keys=True, ensure_ascii=False),
            )
            archive.writestr(
                "evidence-certificate.json",
                json.dumps(certificate, indent=2, sort_keys=True, ensure_ascii=False),
            )
            archive.writestr(
                "audit-events.json",
                json.dumps(record["audit_events"], indent=2, sort_keys=True, ensure_ascii=False),
            )
            archive.writestr(
                "document-history.json",
                json.dumps(history, indent=2, sort_keys=True, ensure_ascii=False),
            )
        safe_title = "-".join(str(record["title"]).lower().split())
        safe_title = "".join(char for char in safe_title if char.isalnum() or char in "-_")[:80] or "document"
        return f"{safe_title}-{envelope_id}.tessaris-evidence.zip", output.getvalue()

    @staticmethod
    def _render_signed_document(record: Mapping[str, Any], proof: Mapping[str, Any]) -> str:
        """Render a portable human-readable completed copy without remote assets."""
        signers = "".join(
            "<tr>"
            f"<td>{escape(str(signer.get('name') or ''))}</td>"
            f"<td>{escape(str(signer.get('email') or ''))}</td>"
            f"<td>{escape(str(signer.get('role') or 'Signer'))}</td>"
            f"<td>{escape(str(signer.get('signed_at') or ''))}</td>"
            f"<td>{escape(str(signer.get('signature_method') or ''))}</td>"
            "</tr>"
            for signer in record.get("signers") or []
        )
        document = record.get("document") or {}
        signed_copy = record.get("signed_copy") or {}
        payload = proof.get("glyphchain_payload") or {}
        chain = proof.get("glyphchain") or {}
        return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{max-width:920px;margin:36px auto;padding:0 24px;color:#172033;font:15px system-ui,sans-serif}}header{{border-top:5px solid #7c3f63;border-bottom:1px solid #d8e0e8;padding:20px 0}}h1{{margin:4px 0}}.meta{{color:#64748b;font-size:12px;overflow-wrap:anywhere}}article{{white-space:pre-wrap;line-height:1.65;padding:28px 0}}table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{border:1px solid #d8e0e8;padding:9px;text-align:left}}th{{background:#f3f5f7}}.notice{{margin-top:24px;border:1px solid #e5c56c;background:#fff9e8;padding:14px;font-size:12px}}</style></head>
<body><header><div class="meta">TESSARIS · COMPLETED SIGNED DOCUMENT</div><h1>{title}</h1>
<div class="meta">Completed {completed_at}<br>Document SHA-256: {document_hash}<br>Signed-copy manifest: {manifest_hash}</div></header>
<article>{content}</article><h2>Signing record</h2><table><thead><tr><th>Signer</th><th>Email</th><th>Role</th><th>Signed at</th><th>Method</th></tr></thead><tbody>{signers}</tbody></table>
<div class="notice"><strong>Evidence reference</strong><br>Proof: {proof_id}<br>GlyphChain status: {chain_status}<br>Transaction: {tx_id}<br><br>This is a human-readable copy of the exact completed document and signing record. Verify document.txt, evidence-certificate.json and the .tessaris-proof receipt locally for cryptographic assurance. This is not a claim of qualified-electronic-signature status.</div></body></html>""".format(
            title=escape(str(record.get("title") or "Signed document")),
            completed_at=escape(str(signed_copy.get("completed_at") or "")),
            document_hash=escape(str(document.get("content_hash") or "")),
            manifest_hash=escape(str(signed_copy.get("manifest_hash") or "")),
            content=escape(str(document.get("content") or "")),
            signers=signers,
            proof_id=escape(str(payload.get("proof_id") or "Not created")),
            chain_status=escape(str(chain.get("status") or "NOT SUBMITTED")),
            tx_id=escape(str(chain.get("tx_id") or "Not finalized")),
        )

    def _activate_lifecycle(self, record: dict[str, Any]) -> None:
        lifecycle = record.setdefault("lifecycle", {
            "status": "DRAFT", "supersedes_envelope_id": None,
            "supersedes_manifest_hash": None, "superseded_by_envelope_id": None,
            "effective_at": None, "notices": [],
        })
        lifecycle["status"] = "ACTIVE"
        lifecycle["effective_at"] = (record.get("signed_copy") or {}).get("completed_at")
        predecessor_id = str(lifecycle.get("supersedes_envelope_id") or "")
        if not predecessor_id:
            return
        predecessor = self._load(str(record["workspace_id"]), predecessor_id)
        self._require_status(predecessor, {"COMPLETED"})
        expected_manifest = str(lifecycle.get("supersedes_manifest_hash") or "")
        actual_manifest = str((predecessor.get("signed_copy") or {}).get("manifest_hash") or "")
        if not expected_manifest or not hmac.compare_digest(expected_manifest, actual_manifest):
            raise LegalSigningError("superseded_document_manifest_changed")
        predecessor_lifecycle = predecessor.setdefault("lifecycle", {
            "status": "ACTIVE", "supersedes_envelope_id": None,
            "supersedes_manifest_hash": None, "superseded_by_envelope_id": None,
            "effective_at": (predecessor.get("signed_copy") or {}).get("completed_at"), "notices": [],
        })
        if predecessor_lifecycle.get("superseded_by_envelope_id") not in {None, record["envelope_id"]}:
            raise LegalSigningError("document_already_superseded")
        predecessor_lifecycle["status"] = "SUPERSEDED"
        predecessor_lifecycle["superseded_by_envelope_id"] = record["envelope_id"]
        predecessor_lifecycle["superseded_at"] = lifecycle["effective_at"]
        self._event(predecessor, "DOCUMENT_SUPERSEDED", "system", {
            "superseded_by_envelope_id": record["envelope_id"],
            "replacement_manifest_hash": (record.get("signed_copy") or {}).get("manifest_hash"),
        })
        self._event(record, "DOCUMENT_REPLACEMENT_ACTIVATED", "system", {
            "supersedes_envelope_id": predecessor_id,
            "supersedes_manifest_hash": actual_manifest,
        })
        self._save(predecessor)

    def _event(self, record: dict[str, Any], event_type: str, actor_id: str, payload: Mapping[str, Any]) -> None:
        events = record.setdefault("audit_events", [])
        core = {"sequence": len(events) + 1, "event_id": f"evt-{uuid4().hex}", "event_type": event_type,
                "actor_id": str(actor_id or "unknown")[:160], "occurred_at": _iso(self.clock()),
                "payload_hash": _digest(dict(payload)), "previous_hash": events[-1]["event_hash"] if events else "GENESIS"}
        events.append({**core, "event_hash": _digest(core)})
        record["updated_at"] = core["occurred_at"]

    def _refresh_expiry(self, record: dict[str, Any]) -> dict[str, Any]:
        if record["status"] not in self.TERMINAL and datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00")) <= self.clock():
            self._deactivate_record_tokens(record)
            record["status"] = "EXPIRED"
            self._event(record, "ENVELOPE_EXPIRED", "system", {})
            self._save(record)
        return record

    @staticmethod
    def _current_signer(record: Mapping[str, Any]) -> dict[str, Any] | None:
        pending = [item for item in record["signers"] if item["status"] == "PENDING"]
        return min(pending, key=lambda item: int(item["order"])) if pending else None

    def _find_by_token(self, token: str) -> tuple[dict[str, Any], dict[str, Any]]:
        supplied = str(token or "")
        if not self.SIGNER_TOKEN_PATTERN.fullmatch(supplied):
            raise LegalSigningError("secure_signing_link_invalid")
        candidate = sha256(supplied.encode("utf-8")).hexdigest()
        indexed = self._read_token_index(candidate)
        if indexed is None and not self._token_index_marker().exists():
            self._rebuild_token_index()
            indexed = self._read_token_index(candidate)
        if indexed is not None:
            try:
                record = self._load(
                    str(indexed["workspace_id"]), str(indexed["envelope_id"]),
                )
            except (KeyError, LegalSigningError):
                self._delete_token_index(candidate)
                raise LegalSigningError("secure_signing_link_invalid") from None
            signer_id = str(indexed.get("signer_id") or "")
            signer = next(
                (item for item in record.get("signers") or [] if str(item.get("signer_id") or "") == signer_id),
                None,
            )
            saved = str((signer or {}).get("token_hash") or "")
            if signer is not None and saved and hmac.compare_digest(saved, candidate):
                return record, signer
            self._delete_token_index(candidate)
            raise LegalSigningError("secure_signing_link_invalid")
        raise LegalSigningError("secure_signing_link_invalid")

    def _rebuild_token_index(self) -> None:
        """Migrate pre-index signing links once, then make misses constant-time."""

        for workspace in self.root.glob("*"):
            if not workspace.is_dir() or workspace.name.startswith("_"):
                continue
            paths = list(workspace.glob("*.enc")) + list(workspace.glob("*.json"))
            for path in paths:
                record = self._read(path)
                if str(record.get("status") or "") in self.TERMINAL:
                    continue
                for signer in record.get("signers") or []:
                    saved = str(signer.get("token_hash") or "")
                    if saved:
                        self._write_token_index(saved, record, signer)
        marker = self._token_index_marker()
        temporary = marker.with_suffix(".tmp")
        temporary.write_text("aion.legal-signing-token-index.v1\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, marker)

    def _token_index_marker(self) -> Path:
        return self.token_index_root / ".migration-complete-v1"

    def _token_index_path(self, token_hash: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", str(token_hash or "")):
            raise LegalSigningError("secure_signing_link_invalid")
        return self.token_index_root / f"{token_hash}.enc"

    def _write_token_index(
        self, token_hash: str, record: Mapping[str, Any], signer: Mapping[str, Any],
    ) -> None:
        path = self._token_index_path(token_hash)
        self.token_index_store.write(
            path,
            {
                "schema_version": "aion.legal-signing-token-index.v1",
                "workspace_id": str(record["workspace_id"]),
                "envelope_id": str(record["envelope_id"]),
                "signer_id": str(signer["signer_id"]),
                "token_hash": token_hash,
            },
            workspace_id=self.TOKEN_INDEX_WORKSPACE,
            record_id=token_hash,
        )

    def _read_token_index(self, token_hash: str) -> dict[str, Any] | None:
        path = self._token_index_path(token_hash)
        if not path.exists():
            return None
        try:
            value = self.token_index_store.read(
                path, workspace_id=self.TOKEN_INDEX_WORKSPACE, record_id=token_hash,
            )
        except Exception:
            return None
        if not hmac.compare_digest(str(value.get("token_hash") or ""), token_hash):
            return None
        return value

    def _delete_token_index(self, token_hash: str) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", str(token_hash or "")):
            self._token_index_path(token_hash).unlink(missing_ok=True)

    def _deactivate_record_tokens(self, record: dict[str, Any]) -> None:
        for signer in record.get("signers") or []:
            self._delete_token_index(str(signer.get("token_hash") or ""))
            signer["token_hash"] = None
            signer["verification_code_hash"] = None

    @staticmethod
    def _require_status(record: Mapping[str, Any], allowed: set[str]) -> None:
        if record.get("status") not in allowed:
            raise LegalSigningError(f"invalid_envelope_state:{record.get('status')}")

    def _workspace_dir(self, workspace_id: str) -> Path:
        safe = "".join(char for char in str(workspace_id) if char.isalnum() or char in "-_")[:120]
        if not safe:
            raise LegalSigningError("workspace_id_required")
        path = self.root / safe
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(self, workspace_id: str, envelope_id: str) -> Path:
        safe = "".join(char for char in str(envelope_id) if char.isalnum() or char in "-_")[:120]
        return self._workspace_dir(workspace_id) / f"{safe}.enc"

    def _legacy_path(self, workspace_id: str, envelope_id: str) -> Path:
        return self._path(workspace_id, envelope_id).with_suffix(".json")

    def _destruction_path(self, workspace_id: str, receipt_id: str) -> Path:
        safe = "".join(char for char in str(receipt_id) if char.isalnum() or char in "-_")[:120]
        if not safe:
            raise LegalSigningError("receipt_id_required")
        folder = self._workspace_dir(workspace_id) / "_destruction"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{safe}.enc"

    def _load(self, workspace_id: str, envelope_id: str) -> dict[str, Any]:
        path = self._path(workspace_id, envelope_id)
        if not path.exists():
            legacy = self._legacy_path(workspace_id, envelope_id)
            if legacy.exists():
                return self._with_governance(self.store.migrate_plaintext(
                    legacy, path, workspace_id=workspace_id, record_id=envelope_id,
                ))
            raise LegalSigningError("envelope_not_found")
        return self._with_governance(self._read(path))

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

    @staticmethod
    def _with_governance(record: dict[str, Any]) -> dict[str, Any]:
        record["records_governance"] = governance_for(record)
        return record

    def _save(self, record: Mapping[str, Any]) -> None:
        path = self._path(str(record["workspace_id"]), str(record["envelope_id"]))
        ensure_workspace_record_write(
            workspace_folder=path.parent,
            record_path=path,
            record_patterns=("*.enc", "*.json"),
            estimated_bytes=estimated_encrypted_record_bytes(record),
            error_type=LegalSigningError,
        )
        self.store.write(
            path, record,
            workspace_id=str(record["workspace_id"]), record_id=str(record["envelope_id"]),
        )
        if str(record.get("status") or "") not in self.TERMINAL:
            for signer in record.get("signers") or []:
                token_hash = str(signer.get("token_hash") or "")
                if token_hash:
                    self._write_token_index(token_hash, record, signer)

    @staticmethod
    def _verification_code_hash(code: str) -> str:
        normalized = "".join(str(code or "").split()).upper()
        return sha256(normalized.encode("utf-8")).hexdigest()

    def _rotate_signer_credentials(self, signer: dict[str, Any]) -> dict[str, str]:
        """Create recover-once signing credentials without persisting either secret."""

        now = _iso(self.clock())
        self._delete_token_index(str(signer.get("token_hash") or ""))
        token = secrets.token_urlsafe(32)
        signer["token_hash"] = sha256(token.encode("utf-8")).hexdigest()
        signer["token_created_at"] = now
        verification_method = str(signer.get("verification_method") or "typed_name_email")
        secure_link = {
            "signer_id": str(signer["signer_id"]),
            "name": str(signer["name"]),
            "email": str(signer["email"]),
            "token": token,
            "verification_method": verification_method,
        }
        if verification_method == "separate_channel_code":
            # Ambiguous characters are omitted so a code can be read over a phone call.
            alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
            code = "".join(secrets.choice(alphabet) for _ in range(10))
            signer["verification_code_hash"] = self._verification_code_hash(code)
            signer["verification_code_created_at"] = now
            secure_link["verification_code"] = code
        else:
            signer["verification_code_hash"] = None
            signer["verification_code_created_at"] = None
        return secure_link

    @staticmethod
    def _send_delivery_resend(record: Mapping[str, Any]) -> dict[str, Any]:
        from backend.modules.aion_business.providers.resend_adapter import ResendAdapter

        attachment = dict(record.get("attachment") or {})
        message = dict(record.get("message") or {})
        result = ResendAdapter().send_email(
            prompt=str(message.get("body_text") or ""),
            metadata={
                "to_emails": [str(record.get("recipient") or "")],
                "subject": str(message.get("subject") or "Completed signed document"),
                "attachments": [{
                    "filename": str(attachment.get("filename") or "signed-evidence.zip"),
                    "content": str(attachment.get("content_base64") or ""),
                }],
                "tags": [
                    {"name": "type", "value": "legal_signed_copy"},
                    {"name": "workspace", "value": str(record.get("workspace_id") or "")[:256]},
                ],
            },
        )
        return {
            "ok": result.ok,
            "provider_request_id": str((result.raw or {}).get("id") or ""),
            "provider_status": "submitted" if result.ok else "failed",
            "error_code": result.error_code,
        }

    @staticmethod
    def _send_delivery_microsoft_graph(record: Mapping[str, Any]) -> dict[str, Any]:
        from backend.modules.aion_business.providers.microsoft_graph_mail_adapter import MicrosoftGraphMailAdapter

        attachment = dict(record.get("attachment") or {})
        message = dict(record.get("message") or {})
        result = MicrosoftGraphMailAdapter(
            access_token=os.getenv("MICROSOFT_GRAPH_ACCESS_TOKEN", ""),
        ).send_traceable_email(
            to_emails=[str(record.get("recipient") or "")],
            subject=str(message.get("subject") or "Completed signed document"),
            body_text=str(message.get("body_text") or ""),
            tracking_id=str(record.get("delivery_id") or ""),
            attachments=[{
                "name": str(attachment.get("filename") or "signed-evidence.zip"),
                "content_type": str(attachment.get("content_type") or "application/zip"),
                "content_base64": str(attachment.get("content_base64") or ""),
            }],
        )
        return {
            "ok": result.ok,
            "provider_request_id": result.provider_request_id,
            "provider_status": "submitted" if result.ok else "failed",
            "error_code": result.error_code,
        }

    @staticmethod
    def _check_delivery_microsoft_graph(record: Mapping[str, Any]) -> dict[str, Any]:
        from backend.modules.aion_business.providers.microsoft_graph_mail_adapter import (
            MicrosoftGraphMessageTraceAdapter,
        )

        result = MicrosoftGraphMessageTraceAdapter(
            access_token=(
                os.getenv("MICROSOFT_GRAPH_MESSAGE_TRACE_ACCESS_TOKEN", "")
                or os.getenv("MICROSOFT_GRAPH_ACCESS_TOKEN", "")
            ),
        ).lookup(
            internet_message_id=str(record.get("provider_request_id") or ""),
            recipient_email=str(record.get("recipient") or ""),
        )
        return {
            "ok": result.ok,
            "found": result.found,
            "trace_id": result.trace_id,
            "internet_message_id": result.internet_message_id,
            "provider_status": result.provider_status,
            "observed_at": result.observed_at,
            "error_code": result.error_code,
        }

    @staticmethod
    def _public(record: Mapping[str, Any]) -> dict[str, Any]:
        value = deepcopy(dict(record))
        for signer in value.get("signers") or []:
            signer.pop("token_hash", None)
            signer.pop("verification_code_hash", None)
        return value
