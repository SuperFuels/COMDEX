"""Provider-neutral, approval-gated browser execution grants.

The connected model may propose semantic browser steps.  AION validates and
authorises them; the model never receives a browser session, credentials or an
execution token.  The Electron executor redeems a short-lived, one-time grant
and returns evidence which is bound into an External Tool Gateway receipt.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import secrets
import threading
import time
from typing import Any, Mapping
from urllib.parse import urlparse
from uuid import uuid4

from backend.services.aion_mission_mode.external_tool_gateway import (
    create_capability_receipt,
    create_capability_registry,
    create_tool_call_request,
    evaluate_tool_call,
)


READ_OPERATIONS = {"open_page", "read_page"}
WRITE_OPERATIONS = {
    "click",
    "click_element",
    "type_text",
    "fill",
    "change_field",
    "select_dropdown",
    "submit",
    "upload",
}
ALLOWED_OPERATIONS = READ_OPERATIONS | WRITE_OPERATIONS


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def browser_tool_contract() -> dict[str, Any]:
    """The identical contract advertised to every approved model."""
    return {
        "schema_version": "aion.browser_tool_contract.v1",
        "provider_neutral": True,
        "planner_role": "approved_connected_model",
        "authority_role": "aion",
        "executor_role": "isolated_browser",
        "operations": sorted(ALLOWED_OPERATIONS),
        "read_operations": sorted(READ_OPERATIONS),
        "approval_required_operations": sorted(WRITE_OPERATIONS),
        "rules": [
            "Models propose semantic steps but never execute them.",
            "Navigation and page reading run only in the isolated browser.",
            "Typing, clicking, submitting, uploading and external changes require exact user approval.",
            "Every execution uses a short-lived one-time grant and produces a visible receipt.",
        ],
    }


def browser_tool_prompt() -> str:
    """Compact protocol appended to every provider in the same form."""
    return (
        "AION BROWSER TOOL CONTRACT: If the request requires operating a website, do not claim it was done. "
        "Return only <AION_BROWSER_PLAN>{\"objective\":\"...\",\"steps\":[...]}</AION_BROWSER_PLAN>. "
        "Each step has operation (open_page, read_page, click, type_text, select_dropdown, submit, upload), "
        "and target containing url for open_page or selector for page elements; type_text also has value. "
        "Use semantic CSS selectors and the fewest steps. AION, not you, controls execution and approval. "
        "For questions not requiring website operation, answer normally."
    )


def extract_browser_plan(text: str) -> dict[str, Any] | None:
    raw = str(text or "")
    start_tag = "<AION_BROWSER_PLAN>"
    end_tag = "</AION_BROWSER_PLAN>"
    start = raw.find(start_tag)
    end = raw.find(end_tag, start + len(start_tag))
    if start < 0 or end < 0:
        return None
    candidate = raw[start + len(start_tag):end].strip()
    try:
        parsed = json.loads(candidate)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _safe_http_url(value: Any) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("browser_step_requires_http_url")
    if parsed.username or parsed.password:
        raise ValueError("browser_url_credentials_blocked")
    return url[:2_000]


def normalise_browser_steps(steps: Any) -> list[dict[str, Any]]:
    if not isinstance(steps, list) or not steps:
        raise ValueError("browser_plan_requires_steps")
    if len(steps) > 30:
        raise ValueError("browser_plan_step_limit_exceeded")
    normalised: list[dict[str, Any]] = []
    for index, raw in enumerate(steps):
        if not isinstance(raw, Mapping):
            raise ValueError("browser_step_must_be_object")
        operation = str(raw.get("operation") or raw.get("type") or "").strip().lower()
        if operation not in ALLOWED_OPERATIONS:
            raise ValueError(f"browser_operation_not_allowed:{operation or 'missing'}")
        raw_target = raw.get("target")
        target = raw_target if isinstance(raw_target, Mapping) else {}
        target_text = str(raw_target or "").strip() if not isinstance(raw_target, Mapping) else ""
        step: dict[str, Any] = {
            "step_id": f"step_{index + 1}",
            "operation": operation,
            "target": {},
            "approval_required": operation in WRITE_OPERATIONS,
        }
        if operation == "open_page":
            step["target"] = {"url": _safe_http_url(target.get("url") or raw.get("url") or target_text)}
        elif operation == "read_page":
            selector = str(target.get("selector") or raw.get("selector") or target_text or "body").strip()
            step["target"] = {"selector": selector[:500] or "body"}
        else:
            selector = str(target.get("selector") or raw.get("selector") or target_text or "").strip()
            if not selector:
                raise ValueError(f"browser_selector_required:{operation}")
            step["target"] = {"selector": selector[:500]}
            if operation in {"type_text", "fill", "change_field", "select_dropdown", "upload"}:
                step["value"] = str(raw.get("value") or "")[:10_000]
        normalised.append(step)
    return normalised


class BrowserHarnessStore:
    """Small local durable grant store scoped to a Tessaris workspace."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "browser_harness" / "state.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                value.setdefault("plans", {})
                value.setdefault("grants", {})
                value.setdefault("receipts", {})
                return value
        except (OSError, ValueError, TypeError):
            pass
        return {"plans": {}, "grants": {}, "receipts": {}}

    def _save(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _public_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
        return {key: deepcopy(value) for key, value in plan.items() if key != "grant_token_hash"}

    def _issue_grant(self, *, state: dict[str, Any], plan: dict[str, Any], now: int) -> tuple[dict[str, Any], str]:
        grant_id = "browser_grant_" + uuid4().hex
        token = secrets.token_urlsafe(32)
        grant = {
            "schema_version": "aion.browser_execution_grant.v1",
            "grant_id": grant_id,
            "plan_id": plan["plan_id"],
            "plan_hash": plan["plan_hash"],
            "token_hash": _hash(token),
            "issued_at": now,
            "expires_at": now + 300,
            "redeemed_at": None,
        }
        state["grants"][grant_id] = grant
        plan["grant_id"] = grant_id
        return grant, token

    def create_plan(
        self,
        *,
        proposal: Mapping[str, Any],
        provider: str,
        model: str,
        workspace_id: str,
        requested_by: str = "aion_chat",
        now: int | None = None,
    ) -> dict[str, Any]:
        issued_at = int(now if now is not None else time.time())
        steps = normalise_browser_steps(proposal.get("steps"))
        plan_id = "browser_plan_" + uuid4().hex
        objective = str(proposal.get("objective") or "Operate the isolated browser").strip()[:500]
        plan: dict[str, Any] = {
            "schema_version": "aion.browser_plan.v1",
            "plan_id": plan_id,
            "workspace_id": workspace_id,
            "provider": str(provider or "").strip(),
            "model": str(model or provider or "").strip(),
            "provider_neutral": True,
            "requested_by": requested_by,
            "objective": objective,
            "steps": steps,
            "approval_step_ids": [step["step_id"] for step in steps if step["approval_required"]],
            "state": "awaiting_user_approval" if any(step["approval_required"] for step in steps) else "ready",
            "created_at": issued_at,
            "approved_at": None,
            "approval_hash": None,
            "grant_id": None,
            "plan_hash": "",
        }
        plan["plan_hash"] = _hash({key: value for key, value in plan.items() if key not in {"plan_hash", "grant_id"}})
        execution_token = ""
        with self._lock:
            state = self._load()
            if plan["state"] == "ready":
                registry = create_capability_registry()
                evaluations = []
                for step in plan["steps"]:
                    tool_name = "browser_navigate" if step["operation"] == "open_page" else "browser_read_page"
                    request = create_tool_call_request(
                        mission_id=plan_id,
                        mission_run_id=plan_id,
                        step_id=step["step_id"],
                        tool_name=tool_name,
                        requested_by="aion_pilot",
                        payload=step,
                    )
                    evaluation = evaluate_tool_call(
                        registry=registry,
                        request=request,
                        evaluation_time=issued_at,
                        caller="aion_pilot",
                    )
                    if not evaluation["allowed"]:
                        raise PermissionError("browser_plan_gateway_blocked:" + ",".join(evaluation["reasons"]))
                    evaluations.append(evaluation)
                plan["gateway_evaluations"] = evaluations
                _, execution_token = self._issue_grant(state=state, plan=plan, now=issued_at)
            state["plans"][plan_id] = plan
            self._save(state)
        public = self._public_plan(plan)
        if execution_token:
            public["execution_token"] = execution_token
        return public

    def approve_plan(
        self,
        *,
        plan_id: str,
        approved_step_ids: list[str],
        approved_by: str,
        now: int | None = None,
    ) -> dict[str, Any]:
        approved_at = int(now if now is not None else time.time())
        with self._lock:
            state = self._load()
            plan = state["plans"].get(plan_id)
            if not isinstance(plan, dict):
                raise KeyError("browser_plan_not_found")
            expected = set(plan.get("approval_step_ids") or [])
            supplied = {str(value) for value in approved_step_ids}
            if supplied != expected:
                raise ValueError("exact_browser_step_approval_required")
            approval = {
                "plan_id": plan_id,
                "plan_hash": plan["plan_hash"],
                "approved_step_ids": sorted(supplied),
                "approved_by": str(approved_by or "business_owner"),
                "approved_at": approved_at,
            }
            approval_hash = _hash(approval)
            registry = create_capability_registry()
            evaluations = []
            for step in plan["steps"]:
                tool_name = "browser_interact" if step["approval_required"] else (
                    "browser_navigate" if step["operation"] == "open_page" else "browser_read_page"
                )
                request = create_tool_call_request(
                    mission_id=plan_id,
                    mission_run_id=plan_id,
                    step_id=step["step_id"],
                    tool_name=tool_name,
                    requested_by="aion_pilot",
                    payload=step,
                    approved_payload_hash=_hash(step) if step["approval_required"] else None,
                    approval_hash=approval_hash if step["approval_required"] else None,
                    approval_expires_at=approved_at + 300 if step["approval_required"] else None,
                )
                evaluation = evaluate_tool_call(
                    registry=registry,
                    request=request,
                    evaluation_time=approved_at,
                    caller="aion_pilot",
                )
                if not evaluation["allowed"]:
                    raise PermissionError("browser_plan_gateway_blocked:" + ",".join(evaluation["reasons"]))
                evaluations.append(evaluation)
            plan.update({
                "state": "ready",
                "approved_at": approved_at,
                "approval_hash": approval_hash,
                "approved_by": approval["approved_by"],
                "gateway_evaluations": evaluations,
            })
            _, execution_token = self._issue_grant(state=state, plan=plan, now=approved_at)
            state["plans"][plan_id] = plan
            self._save(state)
            public = self._public_plan(plan)
            public["execution_token"] = execution_token
            return public

    def redeem_grant(self, *, grant_id: str, execution_token: str, now: int | None = None) -> dict[str, Any]:
        redeemed_at = int(now if now is not None else time.time())
        with self._lock:
            state = self._load()
            grant = state["grants"].get(grant_id)
            if not isinstance(grant, dict):
                raise KeyError("browser_grant_not_found")
            if grant.get("redeemed_at") is not None:
                raise PermissionError("browser_grant_already_redeemed")
            if redeemed_at > int(grant.get("expires_at") or 0):
                raise PermissionError("browser_grant_expired")
            if not secrets.compare_digest(str(grant.get("token_hash") or ""), _hash(execution_token)):
                raise PermissionError("browser_grant_token_invalid")
            plan = state["plans"].get(grant["plan_id"])
            if not isinstance(plan, dict) or plan.get("state") != "ready":
                raise PermissionError("browser_plan_not_ready")
            grant["redeemed_at"] = redeemed_at
            plan["state"] = "executing"
            state["grants"][grant_id] = grant
            state["plans"][plan["plan_id"]] = plan
            self._save(state)
            return {
                "ok": True,
                "grant_id": grant_id,
                "plan_id": plan["plan_id"],
                "plan_hash": plan["plan_hash"],
                "objective": plan["objective"],
                "steps": deepcopy(plan["steps"]),
                "approved_step_ids": deepcopy(plan.get("approval_step_ids") or []),
                "approval_payload_hash": plan.get("approval_hash") or "read_only_grant",
                "expires_at": grant["expires_at"],
            }

    def record_receipt(
        self,
        *,
        grant_id: str,
        result: Mapping[str, Any],
        now: int | None = None,
    ) -> dict[str, Any]:
        completed_at = int(now if now is not None else time.time())
        with self._lock:
            state = self._load()
            grant = state["grants"].get(grant_id)
            if not isinstance(grant, dict) or grant.get("redeemed_at") is None:
                raise PermissionError("browser_grant_not_redeemed")
            plan = state["plans"].get(grant["plan_id"])
            if not isinstance(plan, dict):
                raise KeyError("browser_plan_not_found")
            evaluations = plan.get("gateway_evaluations") or []
            receipt_envelopes = []
            if evaluations:
                for evaluation in evaluations:
                    receipt_envelopes.append(create_capability_receipt(
                        evaluation=evaluation,
                        provider_response=dict(result),
                        evidence_hashes=[_hash(result)],
                        rollback_available=False,
                    ))
            receipt = {
                "schema_version": "aion.browser_execution_receipt.v1",
                "receipt_id": "browser_receipt_" + uuid4().hex,
                "grant_id": grant_id,
                "plan_id": plan["plan_id"],
                "plan_hash": plan["plan_hash"],
                "provider": plan["provider"],
                "model": plan["model"],
                "provider_neutral": True,
                "completed_at": completed_at,
                "ok": bool(result.get("ok")),
                "status": str(result.get("status") or "unknown"),
                "result": deepcopy(dict(result)),
                "gateway_receipts": receipt_envelopes,
                "receipt_hash": "",
            }
            receipt["receipt_hash"] = _hash({key: value for key, value in receipt.items() if key != "receipt_hash"})
            state["receipts"][receipt["receipt_id"]] = receipt
            plan["state"] = "completed" if receipt["ok"] else "failed"
            plan["receipt_id"] = receipt["receipt_id"]
            state["plans"][plan["plan_id"]] = plan
            self._save(state)
            return deepcopy(receipt)

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        with self._lock:
            plan = self._load()["plans"].get(plan_id)
            return self._public_plan(plan) if isinstance(plan, dict) else None
