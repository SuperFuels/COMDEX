from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict
import json
import os
import tempfile

from backend.modules.local_node.contracts_local_node import utc_now_iso


ACTION_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "email_send": {"label": "Send email", "financial": False, "connector": "gmail"},
    "message_send": {"label": "Send chat messages", "financial": False, "connector": "messaging_gateway"},
    "phone_call": {"label": "Make phone calls", "financial": False, "connector": "voice_gateway"},
    "invoice_create": {"label": "Create invoices", "financial": False, "connector": "accounting"},
    "invoice_send": {"label": "Send invoices", "financial": False, "connector": "accounting"},
    "publish": {"label": "Publish content", "financial": False, "connector": "publishing"},
    "purchase": {"label": "Make purchases", "financial": True, "connector": "payments"},
    "payment": {"label": "Make payments", "financial": True, "connector": "payments"},
}

VALID_MODES = {"ask_each_time", "auto_within_limits", "full_access", "blocked"}


def _default_rule(action: str) -> Dict[str, Any]:
    definition = ACTION_DEFINITIONS[action]
    return {
        "mode": "ask_each_time",
        "ask_again": True,
        "currency": "GBP",
        "max_amount": None,
        "updated_at": None,
        "updated_by": None,
        "financial": bool(definition["financial"]),
    }


class PilotAuthorityPolicyStore:
    """Local, workspace-scoped standing authority for real Pilot actions.

    This policy is necessary but never sufficient: a connected adapter, valid
    payload, safety checks and a receipt are still required for execution.
    """

    def __init__(self, base_dir: str) -> None:
        self.path = Path(base_dir) / "pilot_authority_policy.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _default(self, workspace_id: str) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "workspace_id": workspace_id,
            "updated_at": None,
            "rules": {action: _default_rule(action) for action in ACTION_DEFINITIONS},
        }

    def get(self, workspace_id: str) -> Dict[str, Any]:
        payload = self._default(workspace_id)
        if self.path.exists():
            try:
                stored = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(stored, dict):
                    payload.update({key: stored[key] for key in ("schema_version", "workspace_id", "updated_at") if key in stored})
                    for action in ACTION_DEFINITIONS:
                        rule = stored.get("rules", {}).get(action)
                        if isinstance(rule, dict):
                            payload["rules"][action].update(rule)
            except (OSError, ValueError, TypeError):
                pass
        payload["workspace_id"] = workspace_id
        payload["action_definitions"] = deepcopy(ACTION_DEFINITIONS)
        return payload

    def update(self, workspace_id: str, updates: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        payload = self.get(workspace_id)
        rules = payload["rules"]
        now = utc_now_iso()
        for action, patch in (updates or {}).items():
            if action not in ACTION_DEFINITIONS or not isinstance(patch, dict):
                continue
            mode = str(patch.get("mode", rules[action]["mode"]))
            if mode not in VALID_MODES:
                raise ValueError(f"invalid_authority_mode:{action}")
            max_amount = patch.get("max_amount", rules[action].get("max_amount"))
            if max_amount in ("", None):
                max_amount = None
            else:
                max_amount = float(max_amount)
                if max_amount < 0:
                    raise ValueError(f"invalid_max_amount:{action}")
            # Financial actions never receive unlimited standing authority.
            if ACTION_DEFINITIONS[action]["financial"] and mode in {"auto_within_limits", "full_access"} and max_amount is None:
                raise ValueError(f"financial_limit_required:{action}")
            rules[action].update({
                "mode": mode,
                "ask_again": bool(patch.get("ask_again", mode != "blocked")),
                "currency": str(patch.get("currency") or rules[action].get("currency") or "GBP").upper()[:3],
                "max_amount": max_amount,
                "updated_at": now,
                "updated_by": updated_by,
            })
        payload["updated_at"] = now
        serializable = {key: value for key, value in payload.items() if key != "action_definitions"}
        fd, temporary = tempfile.mkstemp(prefix="pilot-authority-", suffix=".json", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(serializable, handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return self.get(workspace_id)

    def evaluate(self, workspace_id: str, action: str, amount: float | None = None, currency: str = "GBP") -> Dict[str, Any]:
        if action not in ACTION_DEFINITIONS:
            return {"authorized": False, "decision": "capability_unknown", "ask_user": False, "action": action}
        policy = self.get(workspace_id)
        rule = policy["rules"][action]
        mode = rule["mode"]
        if mode == "blocked":
            return {"authorized": False, "decision": "blocked_by_owner", "ask_user": bool(rule.get("ask_again")), "action": action, "rule": rule}
        if mode == "ask_each_time":
            return {"authorized": False, "decision": "exact_approval_required", "ask_user": True, "action": action, "rule": rule}
        if ACTION_DEFINITIONS[action]["financial"]:
            limit = rule.get("max_amount")
            if amount is None:
                return {"authorized": False, "decision": "amount_required", "ask_user": True, "action": action, "rule": rule}
            if str(currency or "GBP").upper() != str(rule.get("currency") or "GBP").upper():
                return {"authorized": False, "decision": "currency_outside_authority", "ask_user": True, "action": action, "rule": rule}
            if limit is None or float(amount) > float(limit):
                return {"authorized": False, "decision": "amount_exceeds_authority", "ask_user": True, "action": action, "rule": rule}
        return {"authorized": True, "decision": "standing_authority", "ask_user": False, "action": action, "rule": rule}
