# 📁 codex_executor.py
# Executes compiled glyph logic – symbolic bytecode interpreter

import re
from datetime import datetime

from backend.modules.codex.codex_cost_estimator import CodexCostEstimator
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
from backend.modules.hexcore.memory_engine import MemoryBridge
from backend.modules.state_manager import STATE  # ✅ Pause flag


class CodexExecutor:
    def __init__(self):
        self.log = []
        self.coster = CodexCostEstimator()
        self.metrics = CodexMetrics()

    def execute(self, glyph, context):
        """
        Interpret and execute a glyph structure symbolically.
        Supports logic ops: ⊕, →, ⟲, ↔, ⧖, ⬁, 🧬, 🧭, 🪞
        Emits WebSocket HUD feedback with cost and operator metadata.
        """
        if STATE.is_paused():
            return {
                "status": "paused",
                "reason": "CodexExecutor is paused"
            }

        try:
            timestamp = datetime.utcnow().timestamp()
            self.log.append((glyph, context, timestamp))
            self.metrics.record_execution()

            glyph_stripped = glyph.strip("⟦⟧").strip()

            if "→" not in glyph_stripped:
                return {
                    "status": "ignored",
                    "reason": "No action arrow in glyph"
                }

            lhs, rhs = map(str.strip, glyph_stripped.split("→", 1))

            # Decompose ⟦ Type | Tag : Value ⟧
            match = re.match(r"([^|]+)\|([^:]+):(.+)", lhs)
            if not match:
                return {
                    "status": "error",
                    "error": f"Malformed glyph LHS: {lhs}"
                }

            g_type = match.group(1).strip()
            g_tag = match.group(2).strip()
            g_value = match.group(3).strip()

            # Decompose RHS chain with symbolic operators
            ops_chain = self._decompose_rhs(rhs)

            # Execute each step in the logic chain
            execution_trace = []
            for step in ops_chain:
                op_result = self._resolve_action(step["action"], context, operator=step["operator"])
                execution_trace.append({
                    "operator": step["operator"],
                    "action": step["action"],
                    "result": op_result
                })

            # Estimate symbolic execution cost
            context_info = {
                **context,
                "operator": ops_chain[0]["operator"] if ops_chain else None
            }
            estimate = self.coster.estimate_glyph_cost(glyph, context_info)

            cost_payload = {
                "glyph": glyph,
                "action": ops_chain[0]["action"] if ops_chain else "unknown",
                "source": context.get("source", "unknown"),
                "timestamp": timestamp,
                "cost": round(estimate.total(), 2),
                "detail": {
                    "energy": estimate.energy,
                    "ethics_risk": estimate.ethics_risk,
                    "delay": estimate.delay,
                    "opportunity_loss": estimate.opportunity_loss,
                    "coord": context.get("coord"),
                    "container": context.get("container"),
                    "operator": context_info.get("operator")
                }
            }

            send_codex_ws_event("glyph_execution", cost_payload)

            # ✅ Store in memory
            MemoryBridge.store_memory({
                "source": "codex_executor",
                "type": "execution",
                "glyph": glyph,
                "details": f"Executed {glyph} with ops: {', '.join([s['action'] for s in ops_chain])}",
                "container": context.get("container"),
                "coord": context.get("coord"),
                "cost": cost_payload["cost"],
                "timestamp": timestamp
            })

            return {
                "status": "executed",
                "glyph": glyph,
                "type": g_type,
                "tag": g_tag,
                "value": g_value,
                "operator_chain": [s["operator"] for s in ops_chain],
                "execution_trace": execution_trace,
                "timestamp": timestamp,
                "cost": cost_payload["cost"],
                "detail": cost_payload["detail"]
            }

        except Exception as e:
            self.metrics.record_error()
            return {
                "status": "error",
                "error": str(e)
            }

    def _decompose_rhs(self, rhs: str):
        """
        Splits RHS into a sequence of operations.
        Example: Boot ⊕ Dream ↔ Reflect ⟲ Analyze
        Returns: [{operator, action}, ...]
        """
        pattern = r"(⊕|↔|⟲|⧖|→|⬁|🧬|🧭|🪞)"
        parts = re.split(pattern, rhs)
        result = []
        i = 0
        while i < len(parts):
            if i == 0:
                # First action has implicit → trigger
                result.append({"operator": "→", "action": parts[i].strip()})
                i += 1
            else:
                op = parts[i].strip()
                action = parts[i + 1].strip() if i + 1 < len(parts) else ""
                result.append({"operator": op, "action": action})
                i += 2
        return result

    def _resolve_action(self, action_str, context, operator=None):
        """
        Convert symbolic action string into operation.
        Extendable via CodexLang, GPT plugins, or handlers.
        """
        action_str = action_str.strip()

        # Handle symbolic operators as triggers
        if operator == "⬁":
            return self._trigger("self_rewrite", context)
        elif operator == "🧬":
            return self._trigger("spawn_child_ai", context)
        elif operator == "🧭":
            return self._trigger("explore_codex_space", context)
        elif operator == "🪞":
            return self._trigger("mirror_logic", context)

        # Fallback: action string logic
        if action_str == "Dream":
            return self._trigger("trigger_dream", context)
        elif action_str == "Mutate":
            return self._trigger("propose_dna_mutation", context)
        elif action_str == "Reflect":
            return self._trigger("run_reflection", context)
        elif action_str == "Boot":
            return self._trigger("initiate_boot_sequence", context)
        elif action_str == "Analyze":
            return self._trigger("run_analysis", context)
        elif action_str == "Sync":
            return self._trigger("sync_context", context)
        elif action_str == "Generate":
            return self._trigger("spawn_child_ai", context)
        elif action_str == "Search":
            return self._trigger("explore_codex_space", context)
        elif action_str == "Mirror":
            return self._trigger("mirror_logic", context)
        elif action_str == "Rewrite":
            return self._trigger("self_rewrite", context)
        else:
            return self._trigger("unrecognized_action", context, detail=action_str)

    def _trigger(self, function_name, context, detail=None):
        """
        Simulate symbolic function call.
        """
        return {
            "trigger": function_name,
            "context": context,
            "detail": detail
        }

    def get_log(self):
        return self.log