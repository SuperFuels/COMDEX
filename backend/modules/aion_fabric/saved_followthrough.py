from __future__ import annotations

import json
import os
import ipaddress
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .research import AionTVResearch
from .services import ServiceExecutionHub


class SavedItemFollowThrough:
    """Turn a persona-owned saved item into research or a separately approved proposal."""

    ACTIONS = {"shortlist", "task", "shopping", "trip", "playlist", "learning"}

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "saved_followthrough"
        self.path = self.root / "records.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {"schema_version": "pilot.saved-followthrough.store.v1", "records": [], "updated_at": utc_now_iso()}

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _write(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    def _idempotent(self, *, persona_id: str, idempotency_key: str | None, request_hash: str) -> Dict[str, Any] | None:
        if not idempotency_key:
            return None
        for record in reversed(list(self._read().get("records") or [])):
            if record.get("persona_id") != persona_id or record.get("idempotency_key") != idempotency_key:
                continue
            if record.get("request_hash") != request_hash:
                raise PermissionError("That saved-item request key was already used for a different action")
            return dict(record)
        return None

    @staticmethod
    def _assert_owned(item: Dict[str, Any], persona_id: str) -> None:
        if item.get("status") != "saved" or item.get("persona_id") != persona_id:
            raise PermissionError("A persona-owned saved item is required")

    @staticmethod
    def _query(item: Dict[str, Any]) -> str:
        category = str(item.get("category") or "idea")
        title = str(item.get("title") or "saved item")
        detail = str(item.get("detail") or "")
        prompts = {
            "product": "Compare suitability, current price evidence, delivery, returns, safety and alternatives for",
            "recipe": "Find a reliable recipe, ingredients, timings, substitutions and food-safety notes for",
            "destination": "Research transport, weather, accessibility, costs and useful planning evidence for",
            "music": "Find official listening sources, artist and release information for",
            "learning": "Create an evidence-based learning outline and age-appropriate sources for",
            "idea": "Research evidence, practical options, constraints and next steps for",
        }
        return f"{prompts.get(category, prompts['idea'])} {title}. Context: {detail}"[:500]

    @staticmethod
    def _safe_public_https(url: str) -> str:
        """Only hand a phone a public HTTPS continuation target."""
        try:
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower().rstrip(".")
            if parsed.scheme != "https" or not hostname or hostname == "localhost" or hostname.endswith(".local"):
                return ""
            try:
                address = ipaddress.ip_address(hostname)
            except ValueError:
                return url[:1000]
            if any((address.is_private, address.is_loopback, address.is_link_local, address.is_multicast, address.is_reserved)):
                return ""
            return url[:1000]
        except (TypeError, ValueError):
            return ""

    def research(
        self,
        *,
        item: Dict[str, Any],
        persona_id: str,
        researcher: AionTVResearch,
        idempotency_key: str | None = None,
    ) -> Dict[str, Any]:
        self._assert_owned(item, persona_id)
        request_hash = canonical_hash({"save_id": item.get("save_id"), "action": "research"})
        previous = self._idempotent(persona_id=persona_id, idempotency_key=idempotency_key, request_hash=request_hash)
        if previous:
            return previous
        result = researcher.search(self._query(item), mode="general")
        safe_items = []
        for candidate in list(result.get("items") or [])[:5]:
            if not isinstance(candidate, dict):
                continue
            url = str(candidate.get("url") or "")
            safe_items.append(
                {
                    "title": str(candidate.get("title") or "Evidence result")[:200],
                    "reason": str(candidate.get("reason") or "")[:400],
                    "detail": str(candidate.get("detail") or "")[:240],
                    "url": self._safe_public_https(url),
                }
            )
        record: Dict[str, Any] = {
            "schema_version": "pilot.saved-followthrough.v1",
            "followthrough_id": f"follow_{uuid4().hex}",
            "save_id": item["save_id"],
            "persona_id": persona_id,
            "kind": "research",
            "category": item.get("category"),
            "title": item.get("title"),
            "status": "research_complete",
            "answer": str(result.get("answer") or "Research handoff prepared")[:1000],
            "items": safe_items,
            "provider": str(result.get("provider") or "unknown")[:100],
            "display_label": str(result.get("display_label") or result.get("mode") or "AION")[:100],
            "source_save_hash": item.get("item_hash"),
            "external_effect": False,
            "private_approval_created": False,
            "idempotency_key": str(idempotency_key or "")[:160] or None,
            "request_hash": request_hash,
            "created_at": utc_now_iso(),
        }
        record["record_hash"] = canonical_hash(record)
        self._append(record)
        return record

    @staticmethod
    def _local_scope(item: Dict[str, Any], action: str) -> Dict[str, Any]:
        title = str(item.get("title") or "Saved item")[:240]
        detail = str(item.get("detail") or "")[:500]
        if action == "shortlist":
            return {"title": f"Shortlist for {title}", "source": title, "criteria": ["suitability", "evidence", "cost", "risk"]}
        if action == "task":
            return {"title": f"Follow up: {title}", "notes": detail, "completed": False}
        return {"title": f"Learn more: {title}", "topic": title, "context": detail, "external_links_opened": False}

    @staticmethod
    def _service_scope(item: Dict[str, Any], action: str) -> tuple[str, str, Dict[str, Any]]:
        title = str(item.get("title") or "Saved item")[:240]
        detail = str(item.get("detail") or "")[:500]
        if action == "shopping":
            return "shopping", "prepare_saved_item_purchase", {"item": title, "quantity": 1, "source_context": detail, "purchase": False}
        if action == "trip":
            return "booking", "prepare_saved_destination_trip", {"what": f"Trip to {title}", "date": "", "destination": title, "source_context": detail, "booking": False}
        return "music", "prepare_saved_music", {"request": f"Create a playlist around {title}", "source_context": detail, "account_write": False}

    def prepare_action(
        self,
        *,
        item: Dict[str, Any],
        persona_id: str,
        action: str,
        service_hub: ServiceExecutionHub,
        idempotency_key: str | None = None,
    ) -> Dict[str, Any]:
        self._assert_owned(item, persona_id)
        if action not in self.ACTIONS:
            raise ValueError("Unsupported saved-item follow-through action")
        request_hash = canonical_hash({"save_id": item.get("save_id"), "action": action})
        previous = self._idempotent(persona_id=persona_id, idempotency_key=idempotency_key, request_hash=request_hash)
        if previous:
            return previous
        record: Dict[str, Any] = {
            "schema_version": "pilot.saved-followthrough.v1",
            "followthrough_id": f"follow_{uuid4().hex}",
            "save_id": item["save_id"],
            "persona_id": persona_id,
            "kind": "action",
            "action": action,
            "category": item.get("category"),
            "title": item.get("title"),
            "source_save_hash": item.get("item_hash"),
            "external_effect": False,
            "idempotency_key": str(idempotency_key or "")[:160] or None,
            "request_hash": request_hash,
            "created_at": utc_now_iso(),
        }
        if action in {"shortlist", "task", "learning"}:
            record.update(
                {
                    "status": "local_draft_ready",
                    "exact_scope": self._local_scope(item, action),
                    "service_proposal": None,
                    "private_approval_created": False,
                }
            )
        else:
            service, service_action, parameters = self._service_scope(item, action)
            proposal = service_hub.prepare(
                persona_id=persona_id,
                service=service,
                action=service_action,
                parameters=parameters,
                idempotency_key=f"saved_{idempotency_key}" if idempotency_key else None,
            )
            record.update(
                {
                    "status": "private_service_proposal_ready",
                    "exact_scope": parameters,
                    "service_proposal": proposal,
                    "private_approval_created": True,
                }
            )
        record["record_hash"] = canonical_hash(record)
        self._append(record)
        return record

    def _append(self, record: Dict[str, Any]) -> None:
        state = self._read()
        state["records"] = list(state.get("records") or [])[-199:] + [record]
        self._write(state)

    def refresh_proposal(self, proposal: Dict[str, Any], *, persona_id: str) -> Dict[str, Any]:
        if proposal.get("persona_id") != persona_id:
            raise PermissionError("That service proposal belongs to another private identity")
        state = self._read()
        for record in reversed(list(state.get("records") or [])):
            current = dict(record.get("service_proposal") or {})
            if current.get("proposal_id") == proposal.get("proposal_id"):
                record["service_proposal"] = proposal
                record["record_hash"] = canonical_hash({key: value for key, value in record.items() if key != "record_hash"})
                self._write(state)
                return dict(record)
        raise KeyError("Saved-item follow-through proposal was not found")

    def snapshot(self, *, persona_id: str) -> Dict[str, Any]:
        records = [dict(value) for value in self._read().get("records", []) if isinstance(value, dict) and value.get("persona_id") == persona_id]
        return {"schema_version": "pilot.saved-followthrough.snapshot.v1", "records": records[-50:], "latest": records[-1] if records else None, "count": len(records)}
