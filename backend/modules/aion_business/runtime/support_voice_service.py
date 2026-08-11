"""Dedicated, governed Retell adapter for existing-customer Support calls."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import hmac
import json
from pathlib import Path
import re
import time
from typing import Any
import urllib.request

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.support_case_service import SupportCaseService
from backend.modules.aion_business.runtime.telephony_credentials import get_retell_api_key


def _now() -> str: return datetime.now(UTC).replace(microsecond=0).isoformat()


class SupportVoiceService:
    def __init__(self) -> None:
        self.support = SupportCaseService()
        self.authority = OrganizationAuthorityService(self.support.repository)

    def status(self, workspace_id: str) -> dict[str, Any]:
        record = self._load_deployment(workspace_id)
        return {"provider": "retell", "workspace_id": workspace_id,
                "status": record.get("status") or "deployment_required",
                "agent_id": record.get("agent_id"), "llm_id": record.get("llm_id"),
                "agent_name": record.get("agent_name"), "published": bool(record.get("published")),
                "live_execution_enabled": bool(record.get("live_execution_enabled")),
                "dedicated_support_agent": bool(record.get("agent_id")),
                "external_calls_made": int(record.get("external_calls_made") or 0),
                "governance": {"existing_customers_only": True, "exact_approval_required": True,
                               "refund_or_liability_promises": False,
                               "human_escalation_required": True}}

    def deploy(self, workspace_id: str, *, deployed_by_person_id: str,
               voice_id: str = "retell-Cimo") -> dict[str, Any]:
        access = self._require(workspace_id, deployed_by_person_id, "support.manage")
        existing = self._load_deployment(workspace_id)
        if existing.get("agent_id"):
            verified = self.verify(workspace_id)
            return {"deployment": existing, "verified": verified, "created": False}
        api_key = get_retell_api_key(workspace_id)
        if not api_key: raise PermissionError("retell_api_key_missing")
        prompt = self._prompt(workspace_id)
        recovered = self._discover_existing_agent(api_key)
        if recovered:
            record = self._deployment_record(
                workspace_id, recovered, prompt=prompt,
                deployed_by_person_id=deployed_by_person_id,
                deployment_authority=access, recovered=True,
            )
            self._rehash(record); self._write_deployment(workspace_id, record)
            return {"deployment": record, "verified": self.verify(workspace_id),
                    "created": False, "recovered": True}
        llm = self._request("https://api.retellai.com/create-retell-llm", api_key, {
            "model": "gpt-4.1-mini", "model_temperature": 0,
            "tool_call_strict_mode": True, "start_speaker": "agent",
            "begin_message": "Hello, this is AION, Home Fixed's AI support assistant. How can I help with your existing job or service today?",
            "general_prompt": prompt,
            "general_tools": [{"type": "end_call", "name": "end_call",
                               "description": "End the call politely when the customer confirms there is nothing else to add."}],
            "default_dynamic_variables": {"business_name": "Home Fixed", "case_reference": "not yet known"},
        })
        llm_id = str(llm.get("llm_id") or "")
        if not llm_id: raise ValueError("retell_support_llm_receipt_missing")
        agent = self._request("https://api.retellai.com/create-agent", api_key, {
            "response_engine": {"type": "retell-llm", "llm_id": llm_id},
            "voice_id": voice_id, "agent_name": "AION - Home Fixed Support v1",
            "language": ["en-GB", "es-ES"],
            "version_description": "Governed existing-customer Support agent; no autonomous remedies or liability admissions.",
            "data_storage_setting": "everything_except_pii",
            "data_storage_retention_days": 30,
        })
        agent_id = str(agent.get("agent_id") or "")
        if not agent_id: raise ValueError("retell_support_agent_receipt_missing")
        published = self._request(f"https://api.retellai.com/publish-agent/{agent_id}", api_key, {})
        record = self._deployment_record(
            workspace_id, {**agent, "llm_id": llm_id,
                           "published_version": published.get("version")}, prompt=prompt,
            deployed_by_person_id=deployed_by_person_id,
            deployment_authority=access, recovered=False,
        )
        self._rehash(record); self._write_deployment(workspace_id, record)
        return {"deployment": record, "verified": self.verify(workspace_id), "created": True}

    def _discover_existing_agent(self, api_key: str) -> dict[str, Any] | None:
        agents = self._request("https://api.retellai.com/list-agents?is_latest=true",
                               api_key, None, method="GET")
        rows = agents if isinstance(agents, list) else agents.get("agents", [])
        matches = [row for row in rows
                   if row.get("agent_name") == "AION - Home Fixed Support v1"]
        if not matches: return None
        agent = sorted(matches, key=lambda row: str(row.get("last_modification_timestamp") or
                                                     row.get("created_timestamp") or ""))[-1]
        response_engine = agent.get("response_engine") or {}
        return {**agent, "llm_id": response_engine.get("llm_id")}

    def _deployment_record(self, workspace_id: str, agent: dict[str, Any], *,
                           prompt: str, deployed_by_person_id: str,
                           deployment_authority: dict[str, Any], recovered: bool) -> dict[str, Any]:
        return {"schema_version": "aion.support.retell_deployment.v1",
                "workspace_id": workspace_id, "status": "published_unbound_controlled_use",
                "agent_id": str(agent.get("agent_id") or ""),
                "llm_id": str(agent.get("llm_id") or ""),
                "agent_name": agent.get("agent_name") or "AION - Home Fixed Support v1",
                "voice_id": agent.get("voice_id") or "retell-Cimo",
                "languages": agent.get("language") or ["en-GB", "es-ES"],
                "published": True, "published_version": agent.get("published_version") or agent.get("version"),
                "bound_phone_number": None, "live_execution_enabled": False,
                "external_calls_made": 0,
                "prompt_hash": canonical_contract_hash({"prompt": prompt}),
                "created_at": _now(), "deployed_by_person_id": deployed_by_person_id,
                "deployment_authority": deployment_authority,
                "provider_receipts": {"agent_version": agent.get("version"),
                                      "recovered_after_empty_publish_receipt": recovered}}

    def verify(self, workspace_id: str) -> dict[str, Any]:
        record = self._load_deployment(workspace_id)
        if not record.get("agent_id"): return {"verified": False, "reason": "deployment_missing"}
        api_key = get_retell_api_key(workspace_id)
        versions = self._request(
            f"https://api.retellai.com/get-agent-versions/{record['agent_id']}",
            api_key, None, method="GET")
        rows = versions if isinstance(versions, list) else versions.get("versions", [])
        published = [row for row in rows if row.get("is_published") is True]
        agent = sorted(published, key=lambda row: int(row.get("version") or 0))[-1] if published else {}
        return {"verified": bool(agent) and agent.get("agent_id") == record.get("agent_id"),
                "agent_id": agent.get("agent_id") or record.get("agent_id"),
                "agent_name": agent.get("agent_name") or record.get("agent_name"),
                "voice_id": agent.get("voice_id") or record.get("voice_id"),
                "language": agent.get("language") or record.get("languages"),
                "is_published": bool(agent), "published_version": agent.get("version"),
                "draft_versions": [row.get("version") for row in rows if not row.get("is_published")]}

    def record_webhook(self, workspace_id: str, *, raw_body: bytes, signature: str) -> dict[str, Any]:
        key = get_retell_api_key(workspace_id)
        if not key or not self._verify_signature(raw_body, signature, key):
            raise PermissionError("retell_support_webhook_signature_invalid")
        event = json.loads(raw_body.decode()); call = event.get("call") or {}
        deployment = self._load_deployment(workspace_id)
        if call.get("agent_id") != deployment.get("agent_id"):
            raise PermissionError("retell_event_not_from_support_agent")
        call_id = str(call.get("call_id") or "").strip()
        if not call_id: raise ValueError("retell_support_call_id_missing")
        transcript = call.get("transcript_object") or []
        safe = {"schema_version": "aion.support.retell_event.v1", "workspace_id": workspace_id,
                "event": event.get("event"), "call_id": call_id, "agent_id": call.get("agent_id"),
                "direction": call.get("direction"), "from_number": call.get("from_number"),
                "to_number": call.get("to_number"), "call_status": call.get("call_status"),
                "disconnection_reason": call.get("disconnection_reason"),
                "transcript_object": transcript, "call_analysis": call.get("call_analysis") or {},
                "recording_url_hash": hashlib.sha256(str(call.get("recording_url") or "").encode()).hexdigest()
                                      if call.get("recording_url") else None,
                "received_at": _now()}
        safe["event_hash"] = canonical_contract_hash(safe)
        path = self._root(workspace_id) / "events"; path.mkdir(parents=True, exist_ok=True)
        (path / f"{re.sub(r'[^a-zA-Z0-9_.-]', '-', call_id)}-{int(time.time()*1000)}.json").write_text(
            json.dumps(safe, indent=2, sort_keys=True), encoding="utf-8")
        return safe

    def _prompt(self, workspace_id: str) -> str:
        setup = self.support.ensure_setup(workspace_id)
        return f"""You are AION, the governed AI customer Support assistant for Home Fixed.
You help EXISTING customers with a job, booking, invoice, payment, workmanship or service problem. You are not the Sales agent.

PRIMARY GOAL: understand the issue accurately, identify the customer and relevant job/reference, identify urgency and safety, explain only verified information, and create a clear handoff for a person.
BUSINESS SUPPORT TONE: {setup.get('tone')}. Languages supported: {', '.join(setup.get('languages') or ['en'])}.

REQUIRED INFORMATION, collected naturally rather than as an interrogation:
1. Customer name and best callback route.
2. Job, invoice, booking or case reference if known.
3. What happened, when it happened, and the outcome the customer is seeking.
4. Whether there is immediate danger, vulnerability, property damage or loss of an essential service.
5. Whether the customer wants a human immediately.

ABSOLUTE RULES:
- Disclose that you are an AI assistant.
- Never invent company policy, warranty, legal rights, dates, job status, prices or completed actions.
- Never admit legal liability or blame the customer, worker or company.
- Never promise a refund, compensation, replacement, free revisit, cancellation or completion date.
- Never take payment, change a booking or close a complaint during the call.
- If policy or evidence is unavailable, say a person must check it.
- Honour any request for a person immediately.
- Escalate safety, gas, fire, electrical danger, injury, vulnerability, legal threats, discrimination, data rights, fraud, chargebacks and repeated failures.
- For emergencies tell the caller to contact the appropriate emergency service; do not claim to dispatch help.
- Keep the discussion inside Home Fixed customer Support. Politely refuse unrelated requests.
- Before ending, summarise the facts and agreed next step. State clearly that a person will review the case and that nothing monetary or operational has been approved by the call itself.
"""

    def _require(self, workspace_id: str, person_id: str, capability: str) -> dict[str, Any]:
        decision = self.authority.access_decision(workspace_id, person_id=person_id,
                                                  capability=capability, department_id="department.support")
        if not decision.get("allowed"): raise PermissionError(decision.get("reason") or "support_voice_authority_required")
        return decision

    def _root(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "support/voice"
        path.mkdir(parents=True, exist_ok=True); return path

    def _deployment_path(self, workspace_id: str) -> Path: return self._root(workspace_id) / "retell_deployment.json"
    def _load_deployment(self, workspace_id: str) -> dict[str, Any]:
        path = self._deployment_path(workspace_id)
        if not path.exists(): return {"workspace_id": workspace_id, "status": "deployment_required"}
        record = json.loads(path.read_text(encoding="utf-8")); expected = record.get("deployment_hash")
        copy = dict(record); copy.pop("deployment_hash", None)
        if record.get("workspace_id") != workspace_id or not hmac.compare_digest(str(expected or ""), canonical_contract_hash(copy)):
            raise ValueError("support_voice_deployment_integrity_failed")
        return record
    def _write_deployment(self, workspace_id: str, record: dict[str, Any]) -> None:
        path = self._deployment_path(workspace_id); temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"); temp.replace(path)
    @staticmethod
    def _rehash(record: dict[str, Any]) -> None:
        record.pop("deployment_hash", None); record["deployment_hash"] = canonical_contract_hash(record)
    @staticmethod
    def _verify_signature(raw_body: bytes, signature: str, key: str) -> bool:
        match = re.fullmatch(r"v=(\d+),d=([0-9a-fA-F]+)", str(signature or "").strip())
        if not match: return False
        timestamp, supplied = match.groups()
        if abs(int(time.time() * 1000) - int(timestamp)) > 300000: return False
        expected = hmac.new(key.encode(), raw_body + timestamp.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, supplied.lower())
    @staticmethod
    def _request(url: str, key: str, payload: dict[str, Any] | None,
                 method: str = "POST") -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(url, data=data, method=method,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8").strip()
                return json.loads(raw) if raw else {"ok": True, "status_code": response.status}
        except Exception as exc:
            body = ""
            try: body = exc.read().decode("utf-8")[:1000]
            except Exception: pass
            raise ValueError(f"retell_support_provider_error:{body or exc}") from exc
