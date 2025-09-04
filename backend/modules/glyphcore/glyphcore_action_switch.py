# ─────────────────────────────────────────────
# ⚙️ GlyphCore ActionSwitch – QKD Enforcement + Dispatch
# ─────────────────────────────────────────────
from typing import Dict, Any
from backend.modules.glyphcore.action_policy_map import get_action_policy
from backend.modules.glyphcore.action_context_builder import build_action_context
from backend.modules.glyphwave.qkd.qkd_policy_enforcer import QKDPolicyEnforcer


class ActionSwitch:
    @staticmethod
    def dispatch(op: str, payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Central action dispatcher with enforcement of QKD-required operations.
        """
        action_context = build_action_context(op, payload, context)

        # 🔐 Enforce QKD if required for this op
        policy = get_action_policy(op)
        if policy.get("qkd_required"):
            QKDPolicyEnforcer.enforce_if_required(action_context)

        # 🧠 Dispatch logic (expandable)
        if op == "collapse":
            return ActionSwitch._handle_collapse(payload, action_context)
        elif op == "teleport":
            return ActionSwitch._handle_teleport(payload, action_context)
        elif op == "mutate":
            return ActionSwitch._handle_mutate(payload, action_context)
        else:
            return {"status": "noop", "reason": f"Unknown operation: {op}"}

    @staticmethod
    def _handle_collapse(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder for actual collapse logic
        return {"status": "ok", "op": "collapse", "context": context}

    @staticmethod
    def _handle_teleport(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "ok", "op": "teleport", "context": context}

    @staticmethod
    def _handle_mutate(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "ok", "op": "mutate", "context": context}