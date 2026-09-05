from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class PilotMomentStore:
    """Create portable, rights-aware moment cards without copying protected video."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "moments"
        self.path = self.root / "latest.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.delivery_adapters: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.inbox_path = self.root / "private_phone_inbox.json"
        self.register_delivery_adapter("private_phone", self._deliver_private_phone)

    def register_delivery_adapter(self, route: str, adapter: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        if route not in {"email", "messaging", "pilot_contact", "private_phone"}:
            raise ValueError("Unsupported Moment delivery route")
        self.delivery_adapters[route] = adapter

    def _deliver_private_phone(self, record: Dict[str, Any]) -> Dict[str, Any]:
        recipient = dict(record.get("recipient") or {})
        persona_id = str(recipient.get("persona_id") or "")[:100]
        if not persona_id or recipient.get("route") != "private_phone" or recipient.get("address") != persona_id:
            return {"verified": False}
        try:
            inbox = json.loads(self.inbox_path.read_text(encoding="utf-8")) if self.inbox_path.exists() else []
        except (OSError, json.JSONDecodeError):
            inbox = []
        if not isinstance(inbox, list):
            inbox = []
        card = {
            "moment_id": record.get("moment_id"),
            "persona_id": persona_id,
            "kind": record.get("kind") or "moment",
            "fact_check": record.get("fact_check"),
            "received_at": utc_now_iso(),
            "content_hash": record.get("payload_hash"),
        }
        inbox.append(card)
        temporary = self.inbox_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(inbox[-100:]))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.inbox_path)
        return {"verified": True, "provider_reference": f"private-phone:{record.get('moment_id')}"}

    def _save(self, record: Dict[str, Any]) -> Dict[str, Any]:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(record))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)
        item_path = self.root / f"{record['moment_id']}.json"
        item_temporary = item_path.with_suffix(".tmp")
        item_temporary.write_bytes(canonical_bytes(record))
        os.chmod(item_temporary, 0o600)
        os.replace(item_temporary, item_path)
        return dict(record)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_time(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _require_current(self, moment_id: str) -> Dict[str, Any]:
        record = self.latest()
        if not record or record.get("moment_id") != moment_id:
            raise KeyError("That Pilot Moment is no longer the current private item")
        if not record.get("expires_at"):
            record["schema_version"] = "pilot.moment.v2"
            record["expires_at"] = (self._now() + timedelta(hours=24)).isoformat(timespec="seconds")
            record["recipient"] = None
            record["delivery"] = {"attempts": 0, "receipt": None, "revoked_at": None}
            self._save(record)
        if record.get("deleted_at"):
            raise PermissionError("That Pilot Moment was deleted")
        if self._parse_time(str(record["expires_at"])) <= self._now():
            record["delivery_state"] = "expired"
            self._save(record)
            raise PermissionError("That Pilot Moment has expired")
        return record

    def create(
        self,
        *,
        context: Dict[str, Any],
        request: str,
        issuer_node_id: str,
        public_key: str,
        signer: Callable[[bytes], str],
        recipient: str | None = None,
        requested_seconds: int = 30,
    ) -> Dict[str, Any]:
        app = dict(context.get("app") or {})
        playback = dict(context.get("playback") or {})
        app_text = f"{app.get('id', '')} {app.get('title', '')}".lower()
        if "youtube" in app_text:
            share_mode = "provider_timestamp_link"
        elif "twitch" in app_text:
            share_mode = "provider_native_clip_pending"
        else:
            share_mode = "context_card"
        payload: Dict[str, Any] = {
            "schema_version": "pilot.moment.v2",
            "moment_id": f"moment_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "issuer_node_id": issuer_node_id,
            "request": " ".join(request.split()).strip()[:300],
            "recipient_hint": " ".join((recipient or "").split()).strip()[:100] or None,
            "requested_seconds": max(5, min(int(requested_seconds), 30)),
            "app": app,
            "playback": playback,
            "recent_statement": str(context.get("recent_statement") or "")[:320],
            "context_hash": str(context.get("context_hash") or canonical_hash(context)),
            "share_mode": share_mode,
            "delivery_state": "prepared_not_sent",
            "expires_at": (self._now() + timedelta(hours=24)).isoformat(timespec="seconds"),
            "recipient": None,
            "delivery": {"attempts": 0, "receipt": None, "revoked_at": None},
            "rights": {
                "protected_audio_copied": False,
                "protected_video_copied": False,
                "provider_native_share_preferred": True,
                "card_contains_context_only": True,
            },
        }
        payload_hash = canonical_hash(payload)
        record = {
            **payload,
            "payload_hash": payload_hash,
            "public_key": public_key,
            "signature": signer(canonical_bytes(payload)),
        }
        return self._save(record)

    def create_fact_check(
        self,
        *,
        fact_check: Dict[str, Any],
        request: str,
        issuer_node_id: str,
        public_key: str,
        signer: Callable[[bytes], str],
    ) -> Dict[str, Any]:
        if not fact_check.get("fact_check_id") or not fact_check.get("evidence_hash"):
            raise ValueError("A verified fact-check evidence record is required")
        record = self.create(
            context={
                "app": {},
                "playback": {},
                "recent_statement": str(fact_check.get("statement") or ""),
                "context_hash": str(fact_check.get("evidence_hash")),
            },
            request=request,
            issuer_node_id=issuer_node_id,
            public_key=public_key,
            signer=signer,
        )
        record["kind"] = "fact_check"
        record["fact_check"] = {
            "fact_check_id": fact_check["fact_check_id"],
            "statement": str(fact_check.get("statement") or "")[:500],
            "verdict": str(fact_check.get("verdict") or "Unverifiable")[:40],
            "confidence": float(fact_check.get("confidence") or 0),
            "summary": str(fact_check.get("summary") or "")[:800],
            "sources": [
                {"title": str(item.get("title") or "Evidence source")[:180], "url": str(item.get("url") or "")[:1000]}
                for item in list(fact_check.get("sources") or [])[:5]
                if isinstance(item, dict) and str(item.get("url") or "").startswith("https://")
            ],
            "evidence_hash": fact_check["evidence_hash"],
        }
        record["payload_hash"] = canonical_hash({key: value for key, value in record.items() if key not in {"payload_hash", "signature"}})
        record["signature"] = signer(canonical_bytes({key: value for key, value in record.items() if key not in {"payload_hash", "signature"}}))
        return self._save(record)

    def set_recipient(self, moment_id: str, *, persona_id: str, route: str, recipient: str) -> Dict[str, Any]:
        if route not in {"email", "messaging", "pilot_contact", "private_phone"}:
            raise ValueError("Choose email, messaging, or a Pilot contact")
        recipient = " ".join(recipient.split()).strip()[:240]
        if route == "private_phone":
            recipient = str(persona_id)[:100]
        if len(recipient) < 3 or (route == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient)):
            raise ValueError("Enter a valid private recipient")
        with self._lock:
            record = self._require_current(moment_id)
            if record.get("delivery_state") in {"delivered", "revoked", "deleted"}:
                raise PermissionError("That Moment can no longer be changed")
            record["recipient"] = {"persona_id": persona_id, "route": route, "address": recipient}
            record["recipient_hash"] = canonical_hash({"route": route, "address": recipient})
            record["delivery_state"] = "awaiting_send_confirmation"
            record["preview_hash"] = canonical_hash({
                "moment_id": moment_id,
                "recipient_hash": record["recipient_hash"],
                "content_hash": record["payload_hash"],
            })
            return self._save(record)

    def send(self, moment_id: str, *, persona_id: str, preview_hash: str) -> Dict[str, Any]:
        with self._lock:
            record = self._require_current(moment_id)
            recipient = dict(record.get("recipient") or {})
            if recipient.get("persona_id") != persona_id:
                raise PermissionError("Only the private identity that selected the recipient may send")
            if record.get("delivery_state") == "delivered":
                return dict(record)
            if record.get("delivery_state") not in {"awaiting_send_confirmation", "approved_pending_adapter"} or preview_hash != record.get("preview_hash"):
                raise PermissionError("Review the exact private preview again before sending")
            delivery = dict(record.get("delivery") or {})
            attempts = int(delivery.get("attempts") or 0)
            if attempts >= 3:
                raise PermissionError("Moment delivery rate limit reached")
            delivery["attempts"] = attempts + 1
            route = str(recipient.get("route") or "")
            adapter = self.delivery_adapters.get(route)
            if adapter is None:
                record["delivery_state"] = "approved_pending_adapter"
                delivery["last_error"] = f"No authorized {route} adapter is connected for this identity"
                record["delivery"] = delivery
                return self._save(record)
            result = adapter(dict(record))
            if not isinstance(result, dict) or not result.get("verified"):
                record["delivery_state"] = "delivery_outcome_unknown"
                record["delivery"] = delivery
                self._save(record)
                raise RuntimeError("The delivery provider did not return a verified receipt")
            delivery["receipt"] = {
                "delivery_id": f"moment_delivery_{uuid4().hex}",
                "verified": True,
                "provider_reference": str(result.get("provider_reference") or "")[:300],
                "delivered_at": utc_now_iso(),
                "result_hash": canonical_hash(result),
            }
            record["delivery_state"] = "delivered"
            record["delivery"] = delivery
            return self._save(record)

    def revoke(self, moment_id: str, *, persona_id: str) -> Dict[str, Any]:
        with self._lock:
            record = self._require_current(moment_id)
            recipient = dict(record.get("recipient") or {})
            if recipient and recipient.get("persona_id") != persona_id:
                raise PermissionError("Only the owning private identity may revoke this Moment")
            delivery = dict(record.get("delivery") or {})
            delivery["revoked_at"] = utc_now_iso()
            record["delivery"] = delivery
            record["delivery_state"] = "revoked"
            return self._save(record)

    def delete(self, moment_id: str, *, persona_id: str) -> Dict[str, Any]:
        with self._lock:
            record = self._require_current(moment_id)
            recipient = dict(record.get("recipient") or {})
            if recipient and recipient.get("persona_id") != persona_id:
                raise PermissionError("Only the owning private identity may delete this Moment")
            record["deleted_at"] = utc_now_iso()
            record["delivery_state"] = "deleted"
            record["fact_check"] = None
            record["recent_statement"] = ""
            return self._save(record)

    def report_abuse(self, moment_id: str, *, persona_id: str, reason: str = "unwanted") -> Dict[str, Any]:
        with self._lock:
            record = self._require_current(moment_id)
            reason = re.sub(r"[^a-z0-9 _-]+", "", reason.lower()).strip()[:80] or "unwanted"
            record["abuse_report"] = {
                "reported_by_persona": persona_id,
                "reason": reason,
                "reported_at": utc_now_iso(),
            }
            record["delivery_state"] = "reported_and_blocked"
            return self._save(record)

    def latest(self) -> Dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def snapshot(self) -> Dict[str, Any]:
        try:
            inbox = json.loads(self.inbox_path.read_text(encoding="utf-8")) if self.inbox_path.exists() else []
        except (OSError, json.JSONDecodeError):
            inbox = []
        return {"latest": self.latest(), "private_phone_inbox": inbox[-20:] if isinstance(inbox, list) else []}
