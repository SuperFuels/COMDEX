# 📁 codex_executor.py
# Executes compiled glyph logic – symbolic bytecode interpreter

import re
import asyncio
from datetime import datetime

from backend.modules.codex.codex_cost_estimator import CodexCostEstimator
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.hexcore.memory_engine import MemoryBridge
from backend.modules.consciousness.state_manager import STATE  # ✅ Pause flag
from backend.modules.glyphos.symbolic_entangler import get_entangled_for  # ✅ Entanglement support

# ✅ Global executor instance for benchmarking
executor = None


class CodexExecutor:
    def __init__(self):
        self.log = []
        self.coster = CodexCostEstimator()
        self.metrics = CodexMetrics()
        self.tracer = CodexTrace()

    def execute(self, glyph, context):
        if STATE.is_paused():
            return {"status": "paused", "reason": "CodexExecutor is paused"}

        try:
            timestamp = datetime.utcnow().timestamp()
            self.log.append((glyph, context, timestamp))
            self.metrics.record_execution()

            glyph_stripped = glyph.strip("⟦⟧").strip()

            if glyph_stripped.startswith("Theorem"):
                return self.execute_theorem(glyph_stripped, context, timestamp)

            if "→" not in glyph_stripped:
                return {"status": "ignored", "reason": "No action arrow in glyph"}

            lhs, rhs = map(str.strip, glyph_stripped.split("→", 1))

            match = re.match(r"([^|]+)\|([^:]+):(.+)", lhs)
            if not match:
                return {"status": "error", "error": f"Malformed glyph LHS: {lhs}"}

            g_type = match.group(1).strip()
            g_tag = match.group(2).strip()
            g_value = match.group(3).strip()

            ops_chain = self._decompose_rhs(rhs)

            execution_trace = []
            for step in ops_chain:
                op_result = self._resolve_action(step["action"], context, operator=step["operator"])
                execution_trace.append({
                    "operator": step["operator"],
                    "action": step["action"],
                    "result": op_result
                })

                # ✅ If operator is ↔ (entangled), execute entangled glyphs
                if step["operator"] == "↔":
                    entangled = get_entangled_for(glyph)
                    for partner in entangled:
                        self.log.append((partner, context, timestamp))
                        self.tracer.log_trace({
                            "source": "codex_executor",
                            "glyph": partner,
                            "entangled_from": glyph,
                            "context": context,
                            "timestamp": timestamp
                        })
                        # Avoid infinite loops by not triggering further ↔ here
                        partner_clean = partner.strip("⟦⟧").strip()
                        if "→" in partner_clean:
                            self.execute(partner, context)

            context_info = {**context, "operator": ops_chain[0]["operator"] if ops_chain else None}
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

            # ✅ Primary glyph execution event
            asyncio.create_task(send_codex_ws_event("glyph_execution", cost_payload))

            # 🛰️ Additional lean_theorem_executed event if applicable
            if g_type == "⟦ Theorem ⟧":
                lean_payload = {
                    "type": "lean_theorem_executed",
                    "glyph": glyph,
                    "name": g_tag,
                    "logic": g_value,
                    "operator": ops_chain[0]["operator"] if ops_chain else None,
                    "result": execution_trace,
                    "container": context.get("container"),
                    "coord": context.get("coord"),
                    "timestamp": timestamp
                }
                asyncio.create_task(send_codex_ws_event("lean_theorem_executed", lean_payload))

            self.tracer.log_trace({
                "source": "codex_executor",
                "glyph": glyph,
                "ops_chain": ops_chain,
                "context": context,
                "type": g_type,
                "tag": g_tag,
                "value": g_value,
                "cost": cost_payload["cost"],
                "detail": cost_payload["detail"],
                "timestamp": timestamp
            })

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
            return {"status": "error", "error": str(e)}

    def execute_theorem(self, glyph_stripped: str, context: dict, timestamp: float):
        match = re.match(r"Theorem\s*\|\s*([^:]+):(.+?)\s+via\s+(.+)", glyph_stripped)
        if not match:
            return {"status": "error", "error": f"Malformed theorem glyph: {glyph_stripped}"}

        theorem_id = match.group(1).strip()
        statement = match.group(2).strip()
        proof_ref = match.group(3).strip()

        MemoryBridge.store_memory({
            "source": "codex_executor",
            "type": "lean_theorem_executed",
            "theorem_id": theorem_id,
            "statement": statement,
            "proof": proof_ref,
            "container": context.get("container"),
            "coord": context.get("coord"),
            "timestamp": timestamp
        })

        glyph_str = f"⟦ Theorem | {theorem_id} : {statement} via {proof_ref} ⟧"
        execution_payload = {
            "glyph": glyph_str,
            "action": "validate_theorem",
            "source": context.get("source", "lean_container"),
            "timestamp": timestamp,
            "detail": {
                "container": context.get("container"),
                "coord": context.get("coord")
            }
        }

        lean_payload = {
            "type": "lean_theorem_executed",
            "glyph": glyph_str,
            "name": theorem_id,
            "logic": statement,
            "operator": "⊕",
            "result": [{"operator": "⊕", "action": proof_ref, "result": "proof_accepted"}],
            "container": context.get("container"),
            "coord": context.get("coord"),
            "timestamp": timestamp
        }

        asyncio.create_task(send_codex_ws_event("glyph_execution", execution_payload))
        asyncio.create_task(send_codex_ws_event("lean_theorem_executed", lean_payload))

        return {
            "status": "theorem_validated",
            "theorem_id": theorem_id,
            "statement": statement,
            "proof": proof_ref,
            "timestamp": timestamp
        }

    def _decompose_rhs(self, rhs: str):
        pattern = r"(⊕|↔|⟲|⧖|→|⬁|🧬|🧭|🪞)"
        parts = re.split(pattern, rhs)
        result = []
        i = 0
        while i < len(parts):
            if i == 0:
                result.append({"operator": "→", "action": parts[i].strip()})
                i += 1
            else:
                op = parts[i].strip()
                action = parts[i + 1].strip() if i + 1 < len(parts) else ""
                result.append({"operator": op, "action": action})
                i += 2
        return result

    def _resolve_action(self, action_str, context, operator=None):
        action_str = action_str.strip()

        if operator == "⬁":
            return self._trigger("self_rewrite", context, action_str)
        elif operator == "🧬":
            return self._trigger("spawn_child_ai", context, action_str)
        elif operator == "🧭":
            return self._trigger("explore_codex_space", context, action_str)
        elif operator == "🪞":
            return self._trigger("mirror_logic", context, action_str)

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
        return {
            "trigger": function_name,
            "context": context,
            "detail": detail
        }

    def get_log(self):
        return self.log


# ✅ Exportable function for benchmark_runner.py
def execute_codex_instruction_tree(tree: dict, context: dict = None):
    global executor
    if executor is None:
        executor = CodexExecutor()

    glyph = tree.get("glyph") or "⟦ Logic | Test : Benchmark → Analyze ⟧"
    return executor.execute(glyph, context or {})


# ✅ Add missing method to CodexTrace if not already present
if not hasattr(CodexTrace, "log_trace"):
    def log_trace(self, entry):
        if not hasattr(self, "entries"):
            self.entries = []
        self.entries.append(entry)
    CodexTrace.log_trace = log_trace