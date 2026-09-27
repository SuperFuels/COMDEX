from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
from typing import Any
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


SCHEMA = "tessaris.agent-commerce.v1"
A2A_PROTOCOL_VERSION = "1.0.0"
EXTENSION_URI = "urn:tessaris:agent-commerce:v1"
_LOCK = threading.RLock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _safe_id(value: str, label: str = "identifier") -> str:
    result = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "")).strip("-.")
    if not result or result in {".", ".."}:
        raise ValueError(f"invalid_{label}")
    return result[:160]


class A2ACommerceService:
    def __init__(self, root: str | Path | None = None, public_base_url: str | None = None) -> None:
        self.root = Path(root or AIONBusinessPaths.ROOT / "a2a_commerce")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.public_base_url = str(public_base_url or os.environ.get("TESSARIS_A2A_PUBLIC_BASE_URL") or "http://127.0.0.1:8080").rstrip("/")

    def _path(self, name: str) -> Path:
        return self.root / name

    def _load(self, name: str, default: Any) -> Any:
        path = self._path(name)
        if not path.exists(): return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, name: str, payload: Any) -> None:
        path = self._path(name); path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix="a2a-", suffix=".json", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")); handle.flush(); os.fsync(handle.fileno())
            os.chmod(temporary, 0o600); os.replace(temporary, path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    def _event(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {"event_id": f"a2ae_{uuid.uuid4().hex}", "event_type": event_type, "occurred_at": _iso(),
                 "payload_hash": _hash(payload), "task_id": payload.get("task_id"), "business_id": payload.get("business_id")}
        path = self._path("events.jsonl")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"); handle.flush(); os.fsync(handle.fileno())
        path.chmod(0o600)

    def check_rate_limit(self, *, bucket: str, subject: str, limit: int, window_seconds: int) -> None:
        """Apply a durable fixed-window limit at the external agent boundary."""
        safe_bucket = _safe_id(bucket, "rate_bucket")
        subject_digest = hashlib.sha256(str(subject or "unknown").encode("utf-8")).hexdigest()
        now = _now()
        with _LOCK:
            values = self._load("rate_limits.json", {})
            key = f"{safe_bucket}:{subject_digest}"
            recent = []
            for item in values.get(key, []):
                try:
                    seen = datetime.fromisoformat(str(item).replace("Z", "+00:00")).astimezone(timezone.utc)
                except ValueError:
                    continue
                if (now - seen).total_seconds() < window_seconds:
                    recent.append(_iso(seen))
            if len(recent) >= limit:
                raise PermissionError("a2a_rate_limit_exceeded")
            recent.append(_iso(now))
            values[key] = recent
            # Keep the durable file bounded to active windows only.
            values = {name: entries for name, entries in values.items() if entries}
            self._write("rate_limits.json", values)

    def issue_challenge(self, *, agent_id: str, agent_name: str, public_key_base64: str) -> dict[str, Any]:
        agent_id = _safe_id(agent_id, "agent_id")
        try: key = base64.b64decode(public_key_base64, validate=True)
        except Exception as exc: raise ValueError("invalid_agent_public_key") from exc
        if len(key) != 32: raise ValueError("invalid_agent_public_key")
        existing = self._load("agents.json", {}).get(agent_id)
        if existing and existing.get("status") == "ACTIVE" and existing.get("public_key_base64") != public_key_base64:
            raise ValueError("a2a_agent_id_already_registered")
        challenge_id, challenge = f"ch_{uuid.uuid4().hex}", secrets.token_urlsafe(32)
        record = {"challenge_id": challenge_id, "challenge": challenge, "agent_id": agent_id,
                  "agent_name": str(agent_name)[:160], "public_key_base64": public_key_base64,
                  "expires_at": _iso(_now() + timedelta(minutes=5)), "used": False}
        with _LOCK:
            values = self._load("challenges.json", {})
            values = {key: value for key, value in values.items() if value.get("expires_at", "") > _iso(_now() - timedelta(minutes=10))}
            values[challenge_id] = record; self._write("challenges.json", values)
        return {"challenge_id": challenge_id, "challenge": challenge, "expires_at": record["expires_at"],
                "signature_payload": {"challenge_id": challenge_id, "agent_id": agent_id, "challenge": challenge}}

    def verify_challenge(self, *, challenge_id: str, signature_base64: str) -> dict[str, Any]:
        with _LOCK:
            challenges = self._load("challenges.json", {}); record = challenges.get(challenge_id)
            if not record: raise KeyError("a2a_challenge_not_found")
            if record.get("used"): raise PermissionError("a2a_challenge_already_used")
            if record.get("expires_at", "") <= _iso(): raise PermissionError("a2a_challenge_expired")
            payload = {"challenge_id": challenge_id, "agent_id": record["agent_id"], "challenge": record["challenge"]}
            try:
                Ed25519PublicKey.from_public_bytes(base64.b64decode(record["public_key_base64"], validate=True)).verify(
                    base64.b64decode(signature_base64, validate=True), _canonical(payload))
            except (ValueError, InvalidSignature) as exc: raise PermissionError("invalid_a2a_challenge_signature") from exc
            record["used"] = True; challenges[challenge_id] = record; self._write("challenges.json", challenges)
            agents = self._load("agents.json", {})
            agents[record["agent_id"]] = {"agent_id": record["agent_id"], "agent_name": record["agent_name"],
                "public_key_base64": record["public_key_base64"], "verified_at": _iso(), "status": "ACTIVE"}
            self._write("agents.json", agents)
        return {"agent_id": record["agent_id"], "status": "VERIFIED", "request_signing": {
            "algorithm": "Ed25519", "payload": "METHOD\\nPATH\\nTIMESTAMP\\nNONCE\\nSHA256_BODY",
            "headers": ["X-A2A-Agent-ID", "X-A2A-Timestamp", "X-A2A-Nonce", "X-A2A-Signature"]}}

    def authenticate(self, *, agent_id: str, timestamp: str, nonce: str, signature_base64: str,
                     method: str, path: str, body: bytes) -> dict[str, Any]:
        agent_id, nonce = _safe_id(agent_id, "agent_id"), _safe_id(nonce, "nonce")
        try: observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError as exc: raise PermissionError("invalid_a2a_timestamp") from exc
        if abs((_now() - observed).total_seconds()) > 300: raise PermissionError("stale_a2a_request")
        with _LOCK:
            agents = self._load("agents.json", {}); agent = agents.get(agent_id)
            if not agent or agent.get("status") != "ACTIVE": raise PermissionError("unverified_a2a_agent")
            nonces = self._load("nonces.json", {})
            nonces = {key: value for key, value in nonces.items() if value > _iso(_now() - timedelta(minutes=10))}
            nonce_key = f"{agent_id}:{nonce}"
            if nonce_key in nonces: raise PermissionError("replayed_a2a_request")
            signed = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{hashlib.sha256(body).hexdigest()}".encode()
            try:
                Ed25519PublicKey.from_public_bytes(base64.b64decode(agent["public_key_base64"], validate=True)).verify(
                    base64.b64decode(signature_base64, validate=True), signed)
            except (ValueError, InvalidSignature) as exc: raise PermissionError("invalid_a2a_request_signature") from exc
            nonces[nonce_key] = _iso(); self._write("nonces.json", nonces)
        return agent

    def configure_business(self, business_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        business_id = _safe_id(business_id, "business_id")
        fee_bps = max(0, min(int(profile.get("facilitation_fee_bps", 0)), 5000))
        services = []
        for source in list(profile.get("services") or [])[:500]:
            services.append({"service_id": _safe_id(source.get("service_id"), "service_id"),
                "name": str(source.get("name") or source.get("service_id"))[:200],
                "description": str(source.get("description") or "")[:1000], "locations": [str(x)[:160] for x in source.get("locations", [])[:100]],
                "pricing_mode": str(source.get("pricing_mode") or "quote_required")[:80],
                "base_price_minor": max(0, int(source.get("base_price_minor", 0))), "currency": str(source.get("currency") or "GBP")[:3].upper(),
                "availability": str(source.get("availability") or "human_confirmation_required")[:100],
                "terms_summary": str(source.get("terms_summary") or "")[:1000]})
        value = {"schema_version": SCHEMA, "business_id": business_id, "business_name": str(profile.get("business_name") or business_id)[:200],
                 "description": str(profile.get("description") or "")[:1000], "enabled": bool(profile.get("enabled", True)),
                 "facilitation_fee_bps": fee_bps, "services": services, "updated_at": _iso(),
                 "transaction_policy": {"auto_booking": False, "auto_payment": False, "human_approval_default": True}}
        value["profile_hash"] = _hash(value)
        with _LOCK:
            profiles = self._load("businesses.json", {}); profiles[business_id] = value; self._write("businesses.json", profiles)
        self._event("BUSINESS_PROFILE_CONFIGURED", value)
        return value

    def ensure_business(self, business_id: str, business_name: str | None = None) -> dict[str, Any]:
        """Give every Tessaris workspace a safe inbound channel on first use."""
        business_id = _safe_id(business_id, "business_id")
        existing = self._load("businesses.json", {}).get(business_id)
        if existing:
            return existing
        return self.configure_business(business_id, {
            "business_name": business_name or business_id,
            "description": "Tessaris business agent for guarded commercial requests.",
            "enabled": True,
            "facilitation_fee_bps": 0,
            "services": [],
        })

    def status(self, business_id: str, business_name: str | None = None) -> dict[str, Any]:
        profile = self.ensure_business(business_id, business_name)
        tasks = self.inbox(profile["business_id"])
        agents = self._load("agents.json", {})
        open_states = {"submitted", "working", "input-required", "auth-required"}
        return {
            "schema_version": SCHEMA,
            "protocol_version": A2A_PROTOCOL_VERSION,
            "business": profile,
            "channel": {
                "state": "ACTIVE_LOCAL",
                "public_relay_configured": not self.public_base_url.startswith(("http://127.0.0.1", "http://localhost")),
                "agent_card_url": f"{self.public_base_url}/.well-known/agent-card.json?business_id={profile['business_id']}",
                "agentmap_url": f"{self.public_base_url}/.well-known/agentmap.json?business_id={profile['business_id']}",
            },
            "counts": {
                "verified_external_agents": sum(1 for item in agents.values() if item.get("status") == "ACTIVE"),
                "inbound_tasks": len(tasks),
                "open_tasks": sum(1 for item in tasks if item.get("status", {}).get("state") in open_states),
                "offers_waiting": sum(1 for item in tasks for offer in item.get("offers", []) if offer.get("status") == "OPEN"),
            },
            "inbox": [{
                "task_id": item.get("id"), "state": item.get("status", {}).get("state"),
                "summary": item.get("intent", {}).get("outcome"), "location": item.get("intent", {}).get("location"),
                "service_id": item.get("intent", {}).get("service_id"), "updated_at": item.get("updated_at"),
                "offer_count": len(item.get("offers", [])),
            } for item in tasks[:20]],
            "guardrails": {
                "signed_external_requests": True,
                "replay_protection": True,
                "idempotent_task_creation": True,
                "human_approval_default": True,
                "booking_enabled": False,
                "payment_enabled": False,
            },
        }

    def business(self, business_id: str) -> dict[str, Any]:
        value = self._load("businesses.json", {}).get(_safe_id(business_id, "business_id"))
        if not value or not value.get("enabled"): raise KeyError("a2a_business_not_available")
        return value

    def agent_card(self, business_id: str) -> dict[str, Any]:
        business = self.business(business_id)
        skills = [{"id": item["service_id"], "name": item["name"], "description": item["description"] or item["name"],
                   "tags": ["commerce", item["pricing_mode"]], "examples": []} for item in business["services"]]
        return {"protocolVersion": A2A_PROTOCOL_VERSION, "name": f"{business['business_name']} Business Agent",
                "description": business["description"] or "Tessaris business agent for guarded commercial requests.",
                "url": f"{self.public_base_url}/api/a2a/v1/businesses/{business_id}", "version": "1.0.0",
                "preferredTransport": "HTTP+JSON", "capabilities": {"streaming": False, "pushNotifications": False,
                    "extensions": [{"uri": EXTENSION_URI, "description": "Structured offers, transparent facilitation fees and approval receipts", "required": False}]},
                "defaultInputModes": ["text/plain", "application/json"], "defaultOutputModes": ["application/json"],
                "skills": skills, "securitySchemes": {"agentSignature": {"type": "http", "scheme": "Signature", "description": "Ed25519 challenge registration and per-request signature"}},
                "security": [{"agentSignature": []}], "tessaris": {"business_id": business_id, "profile_hash": business["profile_hash"],
                    "discovery_only": False, "payments_enabled": False, "bookings_enabled": False, "facilitation_fee_disclosed": True}}

    def agentmap(self, business_id: str) -> dict[str, Any]:
        card = self.agent_card(business_id); business = self.business(business_id)
        value = {"agentmap_version": "tessaris.agentmap.v1", "business_id": business_id, "business_name": business["business_name"],
                 "agent_card_url": f"{self.public_base_url}/.well-known/agent-card.json?business_id={business_id}",
                 "accepted_protocols": ["A2A/1.0.0", SCHEMA], "capabilities": business["services"],
                 "commercial_routes": {"create_task": f"{self.public_base_url}/api/a2a/v1/tasks", "task_status": f"{self.public_base_url}/api/a2a/v1/tasks/{{task_id}}",
                    "task_message": f"{self.public_base_url}/api/a2a/v1/tasks/{{task_id}}/messages", "approve_offer": f"{self.public_base_url}/api/a2a/v1/tasks/{{task_id}}/approve"},
                 "authority": {"human_approval_default": True, "payments_enabled": False, "bookings_enabled": False}, "agent_card_hash": _hash(card)}
        value["agentmap_hash"] = _hash(value); return value

    @staticmethod
    def _market_terms(value: str) -> set[str]:
        return {item for item in re.findall(r"[a-z0-9]+", str(value or "").lower()) if len(item) > 1}

    _SERVICE_WORDS = (
        "plumber", "plumbing", "electrician", "electrical", "roofer", "roofing",
        "builder", "building", "carpenter", "carpentry", "painter", "painting",
        "decorator", "cleaner", "cleaning", "gardener", "gardening", "locksmith",
        "mechanic", "heating", "boiler", "drain", "drainage", "handyman", "tiler",
        "plasterer", "removals", "courier", "taxi", "accountant", "solicitor",
        "designer", "developer", "photographer", "caterer",
    )

    @staticmethod
    def _contact_from_text(text: str) -> dict[str, str]:
        email = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.I)
        phone = re.search(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", text)
        result: dict[str, str] = {}
        if email:
            result["email"] = email.group(0)[:254]
        if phone:
            result["phone"] = re.sub(r"\s+", " ", phone.group(0)).strip()[:80]
        return result

    @classmethod
    def _initial_intake_fields(cls, text: str) -> dict[str, Any]:
        clean = " ".join(str(text or "").split())[:4000]
        lowered = clean.lower()
        service = next((word for word in cls._SERVICE_WORDS if re.search(rf"\b{re.escape(word)}\b", lowered)), "")
        timing = ""
        for pattern in (r"\b(?:asap|urgent(?:ly)?|immediately|today|tonight|tomorrow|this (?:morning|afternoon|evening|week|weekend)|next week)\b",):
            found = re.search(pattern, lowered)
            if found:
                timing = found.group(0)
                break
        location = ""
        location_match = re.search(r"\b(?:in|near|around|at)\s+([A-Z][A-Za-z' -]{2,60})(?=$|[,.!?]|\s+(?:today|tomorrow|this|asap|urgent))", clean)
        if location_match:
            location = location_match.group(1).strip()
        problem_signal = any(word in lowered for word in (
            "leak", "broken", "blocked", "damage", "repair", "install", "replace", "not working",
            "quote", "build", "paint", "clean", "move", "fault", "emergency", "service",
        ))
        return {
            "service": service,
            "problem": clean if problem_signal or len(clean.split()) >= 4 else "",
            "location": location,
            "requested_window": timing,
            "contact": cls._contact_from_text(clean),
            "images_answered": False,
            "image_count": 0,
        }

    @staticmethod
    def _intake_question(fields: dict[str, Any]) -> tuple[str | None, str | None]:
        if not fields.get("service"):
            return "service", "What kind of service or specialist do you need?"
        if not fields.get("problem"):
            return "problem", "What has happened, and what outcome do you need?"
        if not fields.get("location"):
            return "location", "Where does the work need to happen? A town or postcode is enough for now."
        if not fields.get("requested_window"):
            return "requested_window", "When do you need someone, and is it urgent?"
        if not fields.get("images_answered"):
            return "images", "Do you have any photos that would help a business understand or price the work?"
        contact = fields.get("contact") or {}
        if not contact.get("email") and not contact.get("phone"):
            return "contact", "What email address or mobile number should we use if a business has a follow-up question?"
        return None, None

    @classmethod
    def _apply_intake_answer(cls, fields: dict[str, Any], *, awaiting: str | None, text: str) -> dict[str, Any]:
        clean = " ".join(str(text or "").split())[:4000]
        lowered = clean.lower()
        if awaiting == "service":
            fields["service"] = next((word for word in cls._SERVICE_WORDS if re.search(rf"\b{re.escape(word)}\b", lowered)), clean[:300])
        elif awaiting == "problem":
            fields["problem"] = clean
        elif awaiting == "location":
            fields["location"] = clean
        elif awaiting == "requested_window":
            fields["requested_window"] = clean
        elif awaiting == "images":
            fields["images_answered"] = True
            fields["images_declined"] = bool(re.search(r"\b(?:no|none|don't|do not|not now)\b", lowered))
        elif awaiting == "contact":
            fields["contact"] = {**dict(fields.get("contact") or {}), **cls._contact_from_text(clean)}
        else:
            inferred = cls._initial_intake_fields(clean)
            for key in ("service", "problem", "location", "requested_window"):
                if inferred.get(key) and not fields.get(key):
                    fields[key] = inferred[key]
            fields["contact"] = {**dict(fields.get("contact") or {}), **dict(inferred.get("contact") or {})}
        return fields

    @classmethod
    def _render_intake(cls, session: dict[str, Any]) -> dict[str, Any]:
        fields = dict(session.get("fields") or {})
        awaiting, question = cls._intake_question(fields)
        session["awaiting"] = awaiting
        session["ready_for_market"] = awaiting is None
        if question:
            reply = question
        else:
            reply = (
                "I have enough information to prepare the service request. Review the job brief, then send it to the market when you are ready. "
                "Businesses can still ask a signed follow-up question before quoting."
            )
        session.setdefault("messages", []).append({"role": "agent", "text": reply, "created_at": _iso()})
        session["updated_at"] = _iso()
        session["ticket"] = {
            "service": fields.get("service") or None,
            "problem": fields.get("problem") or None,
            "location": fields.get("location") or None,
            "requested_window": fields.get("requested_window") or None,
            "contact": fields.get("contact") or {},
            "image_count": int(fields.get("image_count") or 0),
            "missing": [key for key, value in (
                ("service", fields.get("service")), ("problem", fields.get("problem")),
                ("location", fields.get("location")), ("timing", fields.get("requested_window")),
                ("contact", (fields.get("contact") or {}).get("email") or (fields.get("contact") or {}).get("phone")),
            ) if not value],
        }
        return session

    def start_intake(self, *, agent_id: str, text: str, idempotency_key: str) -> dict[str, Any]:
        clean = " ".join(str(text or "").split())[:4000]
        if not clean:
            raise ValueError("intake_message_required")
        key = _safe_id(idempotency_key, "idempotency_key")
        with _LOCK:
            values = self._load("intake_idempotency.json", {})
            composite = f"{agent_id}:{key}"
            if composite in values:
                existing = self._load(f"intakes/{values[composite]}.json", None)
                if existing:
                    return existing
            session_id = f"intake_{uuid.uuid4().hex}"
            session = {
                "schema_version": "tessaris.service-intake.v1", "session_id": session_id,
                "customer_agent_id": agent_id, "state": "gathering", "created_at": _iso(),
                "messages": [{"role": "customer", "text": clean, "created_at": _iso()}],
                "fields": self._initial_intake_fields(clean), "attachments": [],
            }
            session = self._render_intake(session)
            session["state"] = "ready" if session["ready_for_market"] else "gathering"
            self._write(f"intakes/{session_id}.json", session)
            values[composite] = session_id
            self._write("intake_idempotency.json", values)
        self._event("SERVICE_INTAKE_STARTED", {"task_id": session_id, "business_id": None})
        return session

    def continue_intake(self, session_id: str, *, agent_id: str, text: str) -> dict[str, Any]:
        session_id = _safe_id(session_id, "intake_session_id")
        clean = " ".join(str(text or "").split())[:4000]
        if not clean:
            raise ValueError("intake_message_required")
        with _LOCK:
            session = self._load(f"intakes/{session_id}.json", None)
            if not session:
                raise KeyError("service_intake_not_found")
            if session.get("customer_agent_id") != agent_id:
                raise PermissionError("service_intake_agent_mismatch")
            session.setdefault("messages", []).append({"role": "customer", "text": clean, "created_at": _iso()})
            session["fields"] = self._apply_intake_answer(dict(session.get("fields") or {}), awaiting=session.get("awaiting"), text=clean)
            session = self._render_intake(session)
            session["state"] = "ready" if session["ready_for_market"] else "gathering"
            self._write(f"intakes/{session_id}.json", session)
        return session

    def add_intake_attachment(self, session_id: str, *, agent_id: str, filename: str, media_type: str, data_base64: str) -> dict[str, Any]:
        session_id = _safe_id(session_id, "intake_session_id")
        if media_type.lower() not in {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}:
            raise ValueError("unsupported_intake_attachment_type")
        try:
            raw = base64.b64decode(data_base64, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("invalid_intake_attachment") from exc
        if not raw or len(raw) > 8 * 1024 * 1024:
            raise ValueError("intake_attachment_size_invalid")
        with _LOCK:
            session = self._load(f"intakes/{session_id}.json", None)
            if not session:
                raise KeyError("service_intake_not_found")
            if session.get("customer_agent_id") != agent_id:
                raise PermissionError("service_intake_agent_mismatch")
            attachment_id = f"attachment_{uuid.uuid4().hex}"
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", Path(filename).name).strip("-.") or "image"
            extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/heic": ".heic", "image/heif": ".heif"}[media_type.lower()]
            path = self._path(f"intake_attachments/{session_id}/{attachment_id}{extension}")
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.write_bytes(raw); path.chmod(0o600)
            receipt = {"attachment_id": attachment_id, "filename": safe_name[:240], "media_type": media_type.lower(),
                       "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "created_at": _iso()}
            session.setdefault("attachments", []).append(receipt)
            fields = dict(session.get("fields") or {})
            fields["image_count"] = len(session["attachments"]); fields["images_answered"] = True
            session["fields"] = fields
            # Replace the current photo question with an acknowledgement and the next useful question.
            session.setdefault("messages", []).append({"role": "customer", "text": f"Attached {safe_name[:240]}", "created_at": _iso(), "attachment_id": attachment_id})
            session = self._render_intake(session)
            session["state"] = "ready" if session["ready_for_market"] else "gathering"
            self._write(f"intakes/{session_id}.json", session)
        return session

    def search_market(self, *, agent_id: str, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Create a durable, multi-business request and return an evidence-labelled shortlist.

        The initial shortlist may include indicative catalogue prices. Only a
        business-created offer is presented as a live offer.
        """
        key = _safe_id(idempotency_key, "idempotency_key")
        outcome = str(payload.get("outcome") or payload.get("message") or "")[:4000]
        service_query = str(payload.get("service") or payload.get("service_id") or outcome)[:300]
        location = str(payload.get("location") or "")[:300]
        requested_window = str(payload.get("requested_window") or "")[:200]
        budget_minor = max(0, int(payload.get("budget_minor", 0)))
        currency = str(payload.get("currency") or "GBP")[:3].upper()
        requested_terms = self._market_terms(f"{service_query} {outcome}")
        matches: list[tuple[dict[str, Any], dict[str, Any], int]] = []
        for business in self._load("businesses.json", {}).values():
            if not business.get("enabled"):
                continue
            for capability in business.get("services", []):
                capability_terms = self._market_terms(f"{capability.get('service_id')} {capability.get('name')} {capability.get('description')}")
                overlap = len(requested_terms & capability_terms)
                exact = str(payload.get("service_id") or "") == capability.get("service_id")
                if not exact and overlap == 0:
                    continue
                locations = [item.lower() for item in capability.get("locations", [])]
                location_match = not location or not locations or any(location.lower() in item or item in location.lower() for item in locations)
                if not location_match:
                    continue
                matches.append((business, capability, 100 if exact else overlap))
        matches.sort(key=lambda item: (-item[2], item[1].get("base_price_minor") or 10**18, item[0]["business_name"].lower()))
        with _LOCK:
            idempotency = self._load("market_idempotency.json", {})
            composite = f"{agent_id}:{key}"
            if composite in idempotency:
                return self.get_market(idempotency[composite], agent_id=agent_id)
            market_id = f"market_{uuid.uuid4().hex}"
            task_ids: list[str] = []
            for business, capability, _score in matches[:50]:
                task = self.create_task(agent_id=agent_id, idempotency_key=f"{key}-{business['business_id']}-{capability['service_id']}", payload={
                    "business_id": business["business_id"], "message": outcome,
                    "intent": {"service_id": capability["service_id"], "outcome": outcome, "location": location,
                               "requested_window": requested_window, "budget_minor": budget_minor, "currency": currency},
                    "authority": payload.get("authority") or {}, "context_id": market_id,
                })
                task_ids.append(task["id"])
            market = {
                "schema_version": SCHEMA, "market_id": market_id, "customer_agent_id": agent_id,
                "request": {"service": service_query, "outcome": outcome, "location": location,
                            "requested_window": requested_window, "budget_minor": budget_minor, "currency": currency},
                "task_ids": task_ids, "state": "offers_requested" if task_ids else "no_matching_businesses",
                "created_at": _iso(), "updated_at": _iso(),
                "ranking_policy": ["specific_job_match", "requested_location", "live_offer", "evidence_quality", "total_price"],
                "pricing_policy": {"dynamic_pricing_supported": False, "undisclosed_surge_pricing_allowed": False},
            }
            self._write(f"markets/{market_id}.json", market)
            idempotency[composite] = market_id
            self._write("market_idempotency.json", idempotency)
        self._event("MARKET_SEARCH_CREATED", {"task_id": market_id, "business_id": None, "candidate_count": len(task_ids)})
        return self.get_market(market_id, agent_id=agent_id)

    def get_market(self, market_id: str, *, agent_id: str) -> dict[str, Any]:
        market_id = _safe_id(market_id, "market_id")
        market = self._load(f"markets/{market_id}.json", None)
        if not market:
            raise KeyError("a2a_market_search_not_found")
        if market.get("customer_agent_id") != agent_id:
            raise PermissionError("a2a_market_agent_mismatch")
        candidates = []
        profiles = self._load("businesses.json", {})
        for task_id in market.get("task_ids", []):
            task = self.get_task(task_id, agent_id=agent_id)
            profile = profiles.get(task["business_id"], {})
            capability = next((item for item in profile.get("services", []) if item.get("service_id") == task.get("intent", {}).get("service_id")), {})
            live_offer = next((item for item in reversed(task.get("offers", [])) if item.get("status") == "OPEN"), None)
            price = live_offer.get("total_minor") if live_offer else capability.get("base_price_minor") or None
            candidates.append({
                "task_id": task_id, "business_id": task["business_id"], "business_name": profile.get("business_name", task["business_id"]),
                "service_id": capability.get("service_id"), "service_name": capability.get("name"),
                "job_match": "MATCHED", "availability": live_offer.get("availability") if live_offer else capability.get("availability"),
                "price": {"amount_minor": price, "currency": (live_offer or capability).get("currency", market["request"]["currency"]),
                          "evidence": "LIVE_OFFER" if live_offer else ("INDICATIVE_CATALOGUE" if price is not None else "QUOTE_PENDING"),
                          "expires_at": live_offer.get("expires_at") if live_offer else None,
                          "facilitation_fee_minor": live_offer.get("facilitation_fee_minor") if live_offer else None},
                "terms": live_offer.get("terms") if live_offer else capability.get("terms_summary") or "Not supplied yet",
                "reviews": {"state": "NOT_AVAILABLE", "rating": None, "review_count": 0},
                "completed_jobs": {"state": "NOT_VERIFIED", "count": None},
                "offer_hash": live_offer.get("offer_hash") if live_offer else None,
                "next_action": "ACCEPT_EXACT_OFFER" if live_offer else "WAIT_FOR_BUSINESS_OFFER",
            })
        def rank(item: dict[str, Any]) -> tuple:
            evidence = item["price"]["evidence"]
            evidence_rank = {"LIVE_OFFER": 0, "INDICATIVE_CATALOGUE": 1, "QUOTE_PENDING": 2}.get(evidence, 3)
            amount = item["price"]["amount_minor"] if item["price"]["amount_minor"] is not None else 10**18
            return evidence_rank, amount, item["business_name"].lower()
        candidates.sort(key=rank)
        return {**market, "candidates": candidates, "candidate_count": len(candidates),
                "customer_summary": "No eligible businesses found." if not candidates else
                    f"I searched the Tessaris market and found {len(candidates)} matching business{'es' if len(candidates) != 1 else ''}. Live offers are shown ahead of indicative prices; missing reviews and job history are disclosed."}

    def create_task(self, *, agent_id: str, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        business = self.business(str(payload.get("business_id")))
        key = _safe_id(idempotency_key, "idempotency_key")
        with _LOCK:
            idempotency = self._load("idempotency.json", {})
            composite = f"{agent_id}:{key}"
            if composite in idempotency: return self.get_task(idempotency[composite], agent_id=agent_id)
            task_id, context_id = f"task_{uuid.uuid4().hex}", str(payload.get("context_id") or f"ctx_{uuid.uuid4().hex}")[:160]
            intent = dict(payload.get("intent") or {})
            service_id = str(intent.get("service_id") or "")
            service = next((item for item in business["services"] if item["service_id"] == service_id), None)
            task = {"schema_version": SCHEMA, "id": task_id, "contextId": context_id, "business_id": business["business_id"],
                    "customer_agent_id": agent_id, "status": {"state": "input-required" if not service else "working", "timestamp": _iso(),
                    "message": "Business capability selection is required." if not service else "Request received by the business agent."},
                    "intent": {"service_id": service_id, "outcome": str(intent.get("outcome") or payload.get("message") or "")[:4000],
                        "location": str(intent.get("location") or "")[:300], "requested_window": str(intent.get("requested_window") or "")[:200],
                        "budget_minor": max(0, int(intent.get("budget_minor", 0))), "currency": str(intent.get("currency") or "GBP")[:3].upper()},
                    "authority": {"can_negotiate": bool((payload.get("authority") or {}).get("can_negotiate", True)),
                        "max_purchase_minor": max(0, int((payload.get("authority") or {}).get("max_purchase_minor", 0))), "full_purchase": False},
                    "messages": [{"role": "user", "messageId": f"msg_{uuid.uuid4().hex}", "created_at": _iso(), "text": str(payload.get("message") or intent.get("outcome") or "")[:4000]}],
                    "offers": [], "artifacts": [], "created_at": _iso(), "updated_at": _iso(),
                    "safety": {"payment_created": False, "booking_created": False, "external_message_sent": False}}
            self._write(f"tasks/{task_id}.json", task); idempotency[composite] = task_id; self._write("idempotency.json", idempotency)
        self._event("TASK_CREATED", task); return task

    def get_task(self, task_id: str, *, agent_id: str | None = None, business_id: str | None = None) -> dict[str, Any]:
        task_id = _safe_id(task_id, "task_id"); task = self._load(f"tasks/{task_id}.json", None)
        if not task: raise KeyError("a2a_task_not_found")
        if agent_id and task.get("customer_agent_id") != agent_id: raise PermissionError("a2a_task_agent_mismatch")
        if business_id and task.get("business_id") != business_id: raise PermissionError("a2a_task_business_mismatch")
        return task

    def inbox(self, business_id: str) -> list[dict[str, Any]]:
        business_id = _safe_id(business_id, "business_id"); values = []
        for path in sorted((self.root / "tasks").glob("task_*.json"), reverse=True):
            try:
                task = json.loads(path.read_text(encoding="utf-8"))
                if task.get("business_id") == business_id: values.append(task)
            except (OSError, json.JSONDecodeError): pass
        return values[:500]

    def create_offer(self, task_id: str, *, business_id: str, actor_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with _LOCK:
            task = self.get_task(task_id, business_id=business_id); profile = self.business(business_id)
            service_minor = max(0, int(payload.get("service_price_minor", 0))); fee_bps = int(profile["facilitation_fee_bps"])
            fee_minor = int((Decimal(service_minor) * Decimal(fee_bps) / Decimal(10000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            tax_minor = max(0, int(payload.get("tax_minor", 0))); total = service_minor + fee_minor + tax_minor
            offer = {"offer_id": f"offer_{uuid.uuid4().hex}", "business_id": business_id, "service_id": task["intent"]["service_id"],
                     "currency": str(payload.get("currency") or task["intent"]["currency"])[:3].upper(), "service_price_minor": service_minor,
                     "facilitation_fee_bps": fee_bps, "facilitation_fee_minor": fee_minor, "tax_minor": tax_minor, "total_minor": total,
                     "scope": str(payload.get("scope") or "")[:4000], "terms": str(payload.get("terms") or "")[:4000],
                     "availability": str(payload.get("availability") or "human_confirmation_required")[:300],
                     "expires_at": str(payload.get("expires_at") or _iso(_now() + timedelta(minutes=30))), "created_at": _iso(),
                     "created_by_digest": hashlib.sha256(actor_id.encode()).hexdigest(), "status": "OPEN"}
            offer["offer_hash"] = _hash(offer); task["offers"].append(offer)
            task["status"] = {"state": "input-required", "timestamp": _iso(), "message": "Customer approval is required for the exact offer."}
            task["artifacts"] = [{"artifactId": offer["offer_id"], "name": "Commercial offer", "parts": [{"data": offer}]}]
            task["updated_at"] = _iso(); self._write(f"tasks/{task_id}.json", task)
        self._event("OFFER_CREATED", {"task_id": task_id, "business_id": business_id, "offer_hash": offer["offer_hash"]}); return task

    def add_message(self, task_id: str, *, agent_id: str, text: str) -> dict[str, Any]:
        with _LOCK:
            task = self.get_task(task_id, agent_id=agent_id)
            task["messages"].append({"role": "user", "messageId": f"msg_{uuid.uuid4().hex}", "created_at": _iso(), "text": str(text)[:4000]})
            task["status"] = {"state": "working", "timestamp": _iso(), "message": "Customer agent response received."}; task["updated_at"] = _iso()
            self._write(f"tasks/{task_id}.json", task)
        self._event("CUSTOMER_AGENT_MESSAGE", {"task_id": task_id, "business_id": task["business_id"]}); return task

    def approve(self, task_id: str, *, agent_id: str, offer_hash: str, human_confirmed: bool, confirmation: str) -> dict[str, Any]:
        with _LOCK:
            task = self.get_task(task_id, agent_id=agent_id)
            offer = next((item for item in task["offers"] if item.get("offer_hash") == offer_hash and item.get("status") == "OPEN"), None)
            if not offer: raise KeyError("a2a_offer_not_found_or_closed")
            if offer["expires_at"] <= _iso(): raise PermissionError("a2a_offer_expired")
            delegated = task["authority"]["max_purchase_minor"] >= offer["total_minor"] and task["authority"].get("full_purchase") is True
            exact = confirmation == f"APPROVE {offer_hash}"
            if not ((human_confirmed and exact) or delegated): raise PermissionError("exact_human_offer_approval_required")
            offer["status"] = "ACCEPTED"; accepted = {"task_id": task_id, "offer_hash": offer_hash, "agent_id": agent_id,
                "accepted_at": _iso(), "authority": "human_confirmed" if human_confirmed else "delegated", "payment_created": False, "booking_created": False}
            accepted["acceptance_hash"] = _hash(accepted); task["acceptance"] = accepted
            task["status"] = {"state": "completed", "timestamp": _iso(), "message": "Offer negotiation completed; payment and booking remain separate."}
            task["updated_at"] = _iso(); self._write(f"tasks/{task_id}.json", task)
        self._event("OFFER_ACCEPTED", {"task_id": task_id, "business_id": task["business_id"], **accepted}); return task
