import uuid
import json
import requests
import time
import logging
import os
from typing import Any, Dict, List, Optional

from backend.config import GLYPH_API_BASE_URL
from backend.modules.tessaris.thought_branch import ThoughtBranch, BranchNode
from backend.modules.glyphos.glyph_logic import interpret_glyph
from backend.modules.tessaris.tessaris_store import TESSARIS_STORE
from backend.modules.skills.boot_selector import BootSelector
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.tessaris.tessaris_intent_executor import queue_tessaris_intent
from backend.modules.consciousness.memory_bridge import MemoryBridge
from backend.modules.glyphos.glyph_mutator import run_self_rewrite
from backend.modules.glyphos.glyph_generator import GlyphGenerator
from backend.modules.glyphos.glyph_logic import interpret_glyph, detect_contradiction
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.dimensions.container_expander import ContainerExpander
from backend.modules.runtime.container_runtime import collapse_container
from backend.modules.lean.auto_mutate_axioms import suggest_axiom_mutation
from backend.modules.aion_resonance.resonant_heartbeat_monitor import ResonanceHeartbeat
from backend.modules.skills.strategy_planner import ResonantStrategyPlanner
from backend.modules.aion_cognition.action_switch import ActionSwitch
from backend.modules.aion_resonance.reinforcement_mixin import ResonantReinforcementMixin
from backend.modules.lean.lean_tactic_suggester import suggest_tactics
from backend.modules.aion_resonance.resonant_optimizer import get_optimizer


# Codex integration
from backend.modules.codex.codex_mind_model import CodexMindModel
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.codex_cost_estimator import CodexCostEstimator

from backend.modules.skills.goal_engine import GoalEngine
import builtins


# ──────────────────────────────────────────────────────────────
# Quiet hot-loop loggers (prevents spam + tx slowdown)
# ──────────────────────────────────────────────────────────────
logging.getLogger("SQI Event").setLevel(logging.WARNING)
logging.getLogger("knowledge_index").setLevel(logging.WARNING)
logging.getLogger("kg_writer_singleton").setLevel(logging.WARNING)


# ✅ SCI cognition layer
try:
    from backend.modules.aion_language.sci_overlay import sci_emit
except Exception:
    def sci_emit(*a, **k):  # type: ignore
        pass


# ──────────────────────────────────────────────────────────────
# Env toggles (opt-out defaults)
# ──────────────────────────────────────────────────────────────
def _env_bool(name: str, default: str = "0") -> bool:
    v = os.getenv(name, default)
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

# Default OFF: prevents the repeating SQI “resonance_heartbeat_sync” spam
_TESSARIS_SQI_HEARTBEAT = _env_bool("TESSARIS_SQI_HEARTBEAT", "0")

# Default OFF: prevents “✅ Memory stored: tessaris_resonance_update”
_TESSARIS_STORE_RESONANCE_UPDATE = _env_bool("TESSARIS_STORE_RESONANCE_UPDATE", "0")

# Optional: if you want to stop the heartbeat loop entirely
_TESSARIS_HEARTBEAT_LOOP = _env_bool("TESSARIS_HEARTBEAT_LOOP", "1")

# Optional debug prints (keeps hot-loop quiet by default)
_TESSARIS_DEBUG = _env_bool("TESSARIS_DEBUG", "0")


def _kg_log_safe(kg_writer: Any, event_type: str, payload: Dict[str, Any]) -> None:
    """
    Best-effort KG logging.
    - Uses log_event(event_type, payload) if available
    - Else uses append_entry({...}) (dict signature)
    - Else tries inject_glyph(...) if writer supports it
    - Else silently no-ops (no prints, no spam)
    """
    if not kg_writer:
        return
    try:
        if hasattr(kg_writer, "log_event") and callable(getattr(kg_writer, "log_event")):
            kg_writer.log_event(event_type, payload)
            return

        if hasattr(kg_writer, "append_entry") and callable(getattr(kg_writer, "append_entry")):
            # IMPORTANT: append_entry expects a dict entry (not (type, data))
            kg_writer.append_entry({
                "type": event_type,
                "timestamp": payload.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "data": payload,
                "source": "TessarisEngine",
            })
            return

        if hasattr(kg_writer, "inject_glyph") and callable(getattr(kg_writer, "inject_glyph")):
            kg_writer.inject_glyph(
                content=json.dumps(payload, default=str),
                glyph_type=str(event_type),
                metadata={"source": "TessarisEngine"},
                plugin="TessarisEngine",
            )
            return

    except Exception:
        # absolutely do not spam stdout from hot loops
        return


def _quiet_print(*args, **kwargs):
    txt = " ".join(map(str, args))
    if "Synthesizing glyphs" in txt or "connection error" in txt:
        return
    builtins._orig_print(*args, **kwargs)


if not hasattr(builtins, "_orig_print"):
    builtins._orig_print = builtins.print
    builtins.print = _quiet_print


# Register the module to the DNA switch system
DNA_SWITCH.register(__file__)


# ── Goal Trigger ──
def trigger_from_goal(goal_data):
    engine = GoalEngine()
    return engine.process_goal(goal_data)


# ── Utility: Tree Summarizer ──
def _summarize_tree(tree: Any) -> Dict[str, Any]:
    """Minimal structure summary for fallback results."""
    def _depth(n) -> int:
        if isinstance(n, dict):
            ch = n.get("children") or []
            return 1 + (max((_depth(c) for c in ch), default=0) if isinstance(ch, list) else 0)
        if isinstance(n, list):
            return 1 + max((_depth(c) for c in n), default=0)
        return 1

    try:
        size = len(json.dumps(tree, ensure_ascii=False))
    except Exception:
        size = len(str(tree))

    return {"depth": _depth(tree), "size": size}


class TessarisEngine(ResonantReinforcementMixin):
    def __init__(self, container_id: str = "tessaris_engine"):
        self.container_id = container_id
        self.active_branches = []
        self.active_thoughts = {}

        # --- hot-loop throttles (keeps features, stops IO spam) ---
        self._last_resonance_store_ts = 0.0
        self._resonance_store_min_interval_s = 2.0  # tune: 1.0–5.0

        # 🧩 Core subsystems
        from backend.modules.skills.goal_engine import GoalEngine
        self.goal_engine = GoalEngine()
        self.boot_selector = BootSelector()
        self.memlog = MemoryBridge(container_id=container_id)
        self.glyph_generator = GlyphGenerator()
        self.kg_writer = KnowledgeGraphWriter(container_id=container_id)

        # 🧬 Codex integration
        self.codex_mind = CodexMindModel()
        self.codex_metrics = CodexMetrics()
        self.codex_estimator = CodexCostEstimator()

        # 🧭 Strategy Planning (P4)
        self.strategy_planner = ResonantStrategyPlanner()
        print("🧭 TessarisEngine linked to Resonant Strategy Planner.")

        # ⚙️ Action Switch (P5)
        from backend.modules.aion_cognition.action_switch import ActionSwitch
        self.action_switch = ActionSwitch()
        print("⚙️ Tessaris Action Switch initialized.")

        super().__init__("tessaris_engine")
        self.last_reflection_score = 0.0

        self.optimizer = get_optimizer(tick_seconds=30.0)
        self.optimizer.register("tessaris_reasoner", self)
        self.optimizer.start()

        # 💓 Resonance Heartbeat coupling (opt-out)
        self.heartbeat = None
        if _TESSARIS_HEARTBEAT_LOOP:
            self.heartbeat = ResonanceHeartbeat(namespace="tessaris")
            self.heartbeat.register_listener(self._on_heartbeat)
            self.heartbeat.bind_jsonl("data/aion_field/resonant_heartbeat.jsonl")  # optional external feed
            self.heartbeat.start()
            print("💓 TessarisEngine linked to Resonance Heartbeat.")
        else:
            if _TESSARIS_DEBUG:
                print("💤 Tessaris heartbeat loop disabled (TESSARIS_HEARTBEAT_LOOP=0).")

    def _on_heartbeat(self, pulse_data: dict):
        """
        🔁 Called each Resonance Heartbeat tick - evolve Tessaris reasoning weights.
        """
        try:
            delta = pulse_data.get("resonance_delta", 0.0)
            entropy = pulse_data.get("entropy", 0.0)

            # Adjust Codex reasoning dynamics
            if hasattr(self.codex_metrics, "update_entropy"):
                self.codex_metrics.update_entropy(entropy)
            if hasattr(self.codex_mind, "update_resonance"):
                self.codex_mind.update_resonance(delta)

            # Throttled side-effects (memory + KG/SQI) — both opt-out
            now = time.time()
            if (now - self._last_resonance_store_ts) >= self._resonance_store_min_interval_s:

                if _TESSARIS_STORE_RESONANCE_UPDATE:
                    MEMORY.store({
                        "label": "tessaris_resonance_update",
                        "role": "tessaris",
                        "type": "heartbeat_sync",
                        "content": f"Updated reasoning weights (Δ={delta:.4f}, entropy={entropy:.4f})",
                        "data": pulse_data,
                    })

                if _TESSARIS_SQI_HEARTBEAT:
                    event_data = {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "status": "active",
                        "source": "TessarisEngine",
                        "resonance_delta": delta,
                        "entropy": entropy,
                    }
                    _kg_log_safe(self.kg_writer, "resonance_heartbeat_sync", event_data)

                self._last_resonance_store_ts = now

        except Exception as e:
            sci_emit("tessaris_error", f"{str(e)[:200]}")
            if _TESSARIS_DEBUG:
                print(f"[TessarisEngine] ⚠️ Heartbeat processing failed: {e}")

    # ─────────────────────────────────────────────
    # 🧠 Reflection Generator
    # ─────────────────────────────────────────────
    def generate_reflection(self, glyph: Any, context: dict = None, trace: list = None) -> str:
        """
        Generate a reasoning/reflection string for either:
        - a real glyph string
        - plain natural language
        - a dict / structured payload

        Never returns the old hard failure string for non-glyph input.
        """
        context = context or {}
        trace = trace or []

        try:
            parsed = self._parse_glyph(glyph)
            reasoning_parts: List[str] = []

            if parsed and parsed.get("is_glyph", False):
                g_type = parsed.get("type", "Unknown")
                g_tag = parsed.get("tag", "Untitled")
                g_value = parsed.get("value", "")
                action = parsed.get("action", "Reflect")
                reasoning_parts.append(f"{g_type} | {g_tag}: {g_value}")
                reasoning_parts.append(f"Action -> {action}")
            else:
                plain_text = self._coerce_reflection_text(glyph)
                reasoning_parts.append(f"Input -> {plain_text}")

                inferred_mode = "field_report"
                lowered = plain_text.lower()
                if any(word in lowered for word in ("stabilize", "field", "symatics", "coherence", "drift")):
                    inferred_mode = "symatics_reflection"
                elif any(word in lowered for word in ("goal", "plan", "task")):
                    inferred_mode = "goal_reflection"

                reasoning_parts.append(f"Mode -> {inferred_mode}")

            # Include context hints
            if context:
                container = context.get("container", "no-container")
                coord = context.get("coord", "no-coord")
                reasoning_parts.append(f"Context -> Container: {container}, Coord: {coord}")

            # Include execution trace summary
            if trace:
                steps = []
                for step in trace:
                    if isinstance(step, dict):
                        operator = step.get("operator", "?")
                        action = step.get("action", "?")
                        steps.append(f"{operator} {action}")
                    else:
                        steps.append(str(step))
                if steps:
                    reasoning_parts.append(f"Trace -> {' -> '.join(steps)}")

            # Add cost estimation only for real glyph-like strings
            try:
                glyph_text = glyph if isinstance(glyph, str) else json.dumps(glyph, ensure_ascii=False, default=str)
                cost = self.codex_estimator.estimate_glyph_cost(glyph_text, context)
                reasoning_parts.append(f"Cost -> {cost.total():.2f} (E:{cost.energy} / R:{cost.ethics_risk})")
            except Exception as e:
                sci_emit("tessaris_error", f"{str(e)[:200]}")
                reasoning_parts.append(f"Cost -> unavailable ({e})")

            reasoning_text = " | ".join(reasoning_parts)

            MEMORY.store({
                "label": "tessaris_reflection",
                "role": "tessaris",
                "type": "reasoning",
                "content": reasoning_text,
                "data": {
                    "glyph": glyph if isinstance(glyph, str) else self._coerce_reflection_text(glyph),
                    "context": context,
                    "trace": trace,
                }
            })

            _kg_log_safe(self.kg_writer, "reasoning_generated", {
                "glyph": glyph if isinstance(glyph, str) else self._coerce_reflection_text(glyph),
                "reasoning": reasoning_text,
                "context": context,
                "trace_steps": trace,
            })

            try:
                clarity = max(0.1, min(1.0, len(reasoning_text) / 500.0))
                self.update_resonance_feedback(outcome_score=clarity, reason="Reflection clarity")
                self.last_reflection_score = clarity
            except Exception as e:
                sci_emit("tessaris_error", f"{str(e)[:200]}")
                print(f"[⚠️] Resonance feedback failed: {e}")

            return reasoning_text

        except Exception as e:
            sci_emit("tessaris_error", f"{str(e)[:200]}")
            print(f"[⚠️] TessarisEngine.generate_reflection failed: {e}")

            fallback_text = self._coerce_reflection_text(glyph)
            if fallback_text:
                return f"Tessaris reflection -> {fallback_text}"
            return "Reflection unavailable."

    def seed_thought(self, root_symbol: str, source: str = "manual", metadata: dict = {}):
        thought_id = str(uuid.uuid4())
        root = BranchNode(symbol=root_symbol, source=source, metadata=metadata)
        self.active_thoughts[thought_id] = root

        if metadata.get("physics") == "symbolic-expansion":
            self.inflate_hoberman()

        return thought_id, root

    def expand_thought(self, thought_id: str, depth: int = 3):
        root = self.active_thoughts.get(thought_id)
        if not root:
            raise ValueError("Thought not found")
        self._expand_branch(root, depth)
        TESSARIS_STORE.save_branch(ThoughtBranch.from_root(root, origin_id=thought_id))
        return root

    def _expand_branch(self, node: BranchNode, depth: int):
        if depth <= 0:
            return
        children = node.generate_branches()
        for child in children:
            node.add_child(child)
            self._expand_branch(child, depth - 1)

    def inflate_hoberman(self):
        try:
            expand_container(self.container_id)
            print(f"🔵 Expanded Hoberman container {self.container_id}")
        except Exception as e:
            sci_emit("tessaris_error", f"{str(e)[:200]}")
            print(f"[⚠️] Failed to expand container: {e}")

    def collapse_hoberman(self):
        try:
            collapse_container(self.container_id)
            print(f"🔻 Collapsed Hoberman container {self.container_id}")
        except Exception as e:
            sci_emit("tessaris_error", f"{str(e)[:200]}")
            print(f"[⚠️] Failed to collapse container: {e}")

    def process_triggered_cube(self, cube: dict, source: str = "unknown"):
        glyphs = cube.get("glyphs", [])
        if not glyphs:
            return
        symbol = glyphs[0]
        thought_id, root = self.seed_thought(symbol, source=source)
        self.expand_thought(thought_id)
        print(f"[🧠] Thought expanded from glyph {symbol} in {source}")

    def execute_branch(self, branch: ThoughtBranch):
        print(f"\n[🧠] Executing ThoughtBranch from {branch.origin_id} ({len(branch.glyphs)} glyphs)")
        self.kg_writer.log_thought_branch(branch)

        MEMORY.store({
            "label": f"tessaris_exec_{branch.origin_id}",
            "role": "tessaris",
            "type": "thought_branch",
            "content": f"Glyph logic executed from origin {branch.origin_id}",
            "data": {
                "glyphs": branch.glyphs,
                "metadata": branch.metadata,
                "position": branch.position
            }
        })

        for idx, glyph in enumerate(branch.glyphs):
            sci_emit("tessaris_step", f"Glyph {idx} -> {glyph}")
            # 🕊 Soul Law enforcement (global validator)
            from backend.modules.glyphvault.soul_law_validator import soul_law_validator

            if not soul_law_validator.verify_transition(branch.metadata or {}, glyph):
                print(f"⚠️ SoulLaw violation: glyph {idx} blocked -> {glyph}")
                MEMORY.store({
                    "label": "soul_law_violation",
                    "role": "tessaris",
                    "type": "ethics_block",
                    "content": f"Glyph '{glyph}' blocked by SoulLaw.",
                    "data": {"glyph": glyph, "branch_origin": branch.origin_id},
                })
                self.kg_writer.log_event("soul_law_violation", {
                    "glyph": glyph,
                    "branch_origin": branch.origin_id,
                })
                continue  # skip interpretation for this glyph

            # ✅ only reach this if glyph is ethically safe
            try:
                cost = self.codex_estimator.estimate_glyph_cost(glyph, {"source": "tessaris"})
                MEMORY.store({
                    "type": "cost_estimate",
                    "glyph": glyph,
                    "cost": cost.total(),
                    "detail": vars(cost),
                })
                if cost.total() > 7:
                    MEMORY.store({
                        "label": "cost_warning",
                        "role": "tessaris",
                        "type": "self_reflection",
                        "content": f"⚠️ High future cost predicted for glyph {glyph}",
                        "data": {
                            "glyph": glyph,
                            "total_cost": cost.total(),
                            "breakdown": vars(cost)
                        }
                    })
                    print(f"⚠️ Self-reflection: high-cost glyph {glyph} -> total cost {cost.total():.2f}")

                result = interpret_glyph(glyph, context={
                    "branch": branch,
                    "position": branch.position,
                    "index": idx,
                    "metadata": branch.metadata
                })
                print(f"  ➤ Glyph {idx}: {glyph} -> {result}")

                coord = branch.position.get("coord")
                container_path = branch.metadata.get("container_path") if branch.metadata else None

                if "⊥" in str(result) or detect_contradiction(str(result)) or cost.total() > 9:
                    if coord and container_path:
                        reason = "contradiction" if "⊥" in str(result) else "high_cost" if cost.total() > 9 else "unknown"
                        print(f"⬁ Triggering fallback rewrite for glyph: {glyph} due to {reason}")

                        MEMORY.store({
                            "label": "fallback_rewrite",
                            "role": "tessaris",
                            "type": "self_rewrite",
                            "content": f"⬁ Rewrite triggered for glyph {glyph} due to {reason}.",
                            "data": {
                                "glyph": glyph,
                                "reason": reason,
                                "cost": cost.total(),
                                "coord": coord
                            }
                        })

                        self.kg_writer.log_event("self_rewrite_triggered", {
                            "glyph": glyph,
                            "reason": reason,
                            "cost": cost.total(),
                            "coord": coord,
                        })

                        try:
                            replacements = run_lean_self_rewrite(glyph)
                            if replacements:
                                self.kg_writer.log_event("self_rewrite_result", {
                                    "replacements": replacements,
                                    "coord": coord,
                                })
                                self.memory_engine.replace_glyph_at(container_path, coord, replacements[0])
                                print("♻️ Fallback self-rewrite succeeded via Lean.")
                            else:
                                print("⚠️ Fallback rewrite returned no results.")
                        except Exception as e:
                            sci_emit("tessaris_error", f"{str(e)[:200]}")
                            print(f"⚠️ Fallback rewrite failed: {e}")

                self.codex_mind.observe(glyph)
                self.codex_metrics.record_execution()

                if glyph.strip().startswith("⟦ Write") or glyph.strip().startswith("⟦ Mutate"):
                    if coord and container_path:
                        self.kg_writer.log_event("self_rewrite_triggered", {
                            "glyph": glyph,
                            "reason": "contradiction" if "⊥" in str(result) else "error",
                            "cost": cost.total(),
                            "coord": coord,
                        })
                        try:
                            replacements = run_lean_self_rewrite(glyph)
                            if replacements:
                                self.kg_writer.log_event("self_rewrite_result", {
                                    "replacements": replacements,
                                    "coord": coord,
                                })
                                self.memory_engine.replace_glyph_at(container_path, coord, replacements[0])
                                print("♻️ Self-rewriting glyph executed via Lean.")
                            else:
                                print("⚠️ Self-rewrite returned no results.")
                        except Exception as e:
                            sci_emit("tessaris_error", f"{str(e)[:200]}")
                            print(f"⚠️ Lean-based self-rewrite failed: {e}")

                        # 🧠 Tactic suggestion
                        if glyph.strip().startswith("⟦ Mutate"):
                            try:
                                tactic_suggestion = suggest_tactics(glyph)
                                if tactic_suggestion:
                                    print(f"🧠 Suggested tactic: {tactic_suggestion}")
                                    self.kg_writer.log_event("tactic_suggestion", {
                                        "glyph": glyph,
                                        "suggestion": tactic_suggestion,
                                        "coord": coord,
                                    })
                            except Exception as e:
                                sci_emit("tessaris_error", f"{str(e)[:200]}")
                                print(f"⚠️ Tactic suggestion failed: {e}")

                        # 🧬 Axiom mutation
                        if "⊥" in str(result):
                            try:
                                axiom_mutation = suggest_axiom_mutation(glyph)
                                if axiom_mutation:
                                    print(f"🧬 Suggested axiom mutation: {axiom_mutation}")
                                    self.kg_writer.log_event("axiom_mutation_suggestion", {
                                        "glyph": glyph,
                                        "suggestion": axiom_mutation,
                                        "coord": coord,
                                    })
                            except Exception as e:
                                sci_emit("tessaris_error", f"{str(e)[:200]}")
                                print(f"⚠️ Axiom mutation suggestion failed: {e}")

                        # 🔁 Fallback rewriter
                        self.kg_writer.log_event("self_rewrite_triggered", {
                            "glyph": glyph,
                            "reason": "error",
                            "coord": coord,
                            "cost": cost.total() if 'cost' in locals() else None,
                        })
                        success = run_self_rewrite(container_path, coord)
                        print("♻️ Fallback symbolic rewrite executed." if success else "⚠️ Fallback rewrite failed.")

                if "⟲" in glyph and "Reflect" in str(result):
                    MEMORY.store({
                        "label": "tessaris_reflection",
                        "role": "tessaris",
                        "type": "self_reflection",
                        "content": f"Reflected on glyph {glyph}",
                        "data": {"glyph": glyph}
                    })
                    print(f"🔁 Reflection triggered from ⟲ glyph")

                self._maybe_create_goal(glyph, branch)
                self._maybe_suggest_boot(glyph, branch)

            except Exception as e:
                sci_emit("tessaris_error", f"{str(e)[:200]}")
                print(f"  ⚠️ Error interpreting glyph {glyph}: {e}")
                self.codex_metrics.record_error()

                coord = branch.position.get("coord")
                container_path = branch.metadata.get("container_path") if branch.metadata else None
                result_str = str(locals().get("result", ""))

                if coord and container_path:
                    MEMORY.store({
                        "label": "fallback_rewrite_error",
                        "role": "tessaris",
                        "type": "self_rewrite",
                        "content": f"⬁ Rewrite triggered from glyph error: {glyph}",
                        "data": {
                            "glyph": glyph,
                            "exception": str(e),
                            "coord": coord
                        }
                    })

                    _kg_log_safe(self.kg_writer, "self_rewrite_triggered", {
                        "glyph": glyph,
                        "reason": "error",
                        "cost": cost.total() if 'cost' in locals() else None,
                        "coord": coord,
                    })

                    # 1) Try Lean rewrite suggestions
                    try:
                        replacements = run_lean_self_rewrite(glyph)
                        if replacements:
                            _kg_log_safe(self.kg_writer, "self_rewrite_result", {
                                "replacements": replacements,
                                "coord": coord,
                            })
                            self.memory_engine.replace_glyph_at(container_path, coord, replacements[0])
                            print("⬁ Auto-rewrite from error succeeded via Lean.")
                            success = True
                        else:
                            print("⚠️ Lean rewrite returned no replacements.")
                            success = False
                    except Exception as inner:
                        sci_emit("tessaris_error", f"{str(inner)[:200]}")
                        print(f"⚠️ Lean rewrite failed: {inner}")
                        success = False

                    # 2) Tactic suggestion for ⟦ Mutate glyphs
                    if glyph.strip().startswith("⟦ Mutate"):
                        try:
                            tactic_suggestion = suggest_tactics(glyph)
                            if tactic_suggestion:
                                print(f"🧠 Suggested tactic: {tactic_suggestion}")
                                _kg_log_safe(self.kg_writer, "tactic_suggestion", {
                                    "glyph": glyph,
                                    "suggestion": tactic_suggestion,
                                    "coord": coord,
                                })
                        except Exception as inner:
                            sci_emit("tessaris_error", f"{str(inner)[:200]}")
                            print(f"⚠️ Tactic suggestion failed: {inner}")

                    # 3) Axiom mutation suggestion (only if we have a contradiction signal)
                    if "⊥" in result_str:
                        try:
                            axiom_mutation = suggest_axiom_mutation(glyph)
                            if axiom_mutation:
                                print(f"🧬 Axiom mutation suggestion: {axiom_mutation}")
                                _kg_log_safe(self.kg_writer, "axiom_mutation_suggestion", {
                                    "glyph": glyph,
                                    "suggestion": axiom_mutation,
                                    "coord": coord,
                                })
                        except Exception as inner:
                            sci_emit("tessaris_error", f"{str(inner)[:200]}")
                            print(f"⚠️ Axiom mutation failed: {inner}")

                    # 4) Final fallback: symbolic self-rewrite
                    _kg_log_safe(self.kg_writer, "self_rewrite_triggered", {
                        "glyph": glyph,
                        "reason": "error",
                        "coord": coord,
                        "cost": cost.total() if 'cost' in locals() else None,
                    })
                    try:
                        success = run_self_rewrite(container_path, coord)
                    except Exception:
                        success = False
                    print("⬁ Fallback symbolic rewrite executed." if success else "⚠️ Fallback auto-rewrite failed.")

                if "⟲" in glyph and "Reflect" in result_str:
                    MEMORY.store({
                        "label": "tessaris_reflection",
                        "role": "tessaris",
                        "type": "self_reflection",
                        "content": f"Reflected on glyph {glyph}",
                        "data": {"glyph": glyph}
                    })
                    print(f"🔁 Reflection triggered from ⟲ glyph")

                self._maybe_create_goal(glyph, branch)
                self._maybe_suggest_boot(glyph, branch)

    def _send_synthesis(self, branch: ThoughtBranch):
        try:
            payload = {
                "glyphs": branch.glyphs,
                "metadata": branch.metadata,
                "source": "tessaris_engine",
                "origin_id": branch.origin_id
            }
            response = requests.post(f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs", json=payload)
            if response.ok:
                print(f"[✨] Synthesized glyphs: {response.json()}")
            else:
                print(f"[⚠️] Synthesis failed: {response.status_code}")
        except Exception as e:
            sci_emit("tessaris_error", f"{str(e)[:200]}")
            print(f"[❌] Glyph synthesis error: {e}")

    def _generate_from_branch(self, branch: ThoughtBranch):
        try:
            generated = self.glyph_generator.generate_from_text(
                input_text=" ".join(branch.glyphs),
                context="tessaris"
            )
            print(f"[🧬] Re-generated glyphs: {generated}")
        except Exception as e:
            sci_emit("tessaris_error", f"{str(e)[:200]}")
            print(f"[❌] Glyph generation error: {e}")

    def _maybe_create_goal(self, glyph: str, branch: ThoughtBranch):
        if "Goal" in glyph or glyph.startswith("⟦ Goal"):
            parsed = self._parse_glyph(glyph)
            if parsed:
                title = parsed.get("tag", "Unnamed Goal")
                desc = parsed.get("value", "Generated from glyph.")
                goal = self.goal_engine.create_goal_from_glyph(title, desc)
                print(f"[🎯] New goal proposed: {goal.get('name')}")
                MEMORY.store({
                    "label": "tessaris_goal_created",
                    "role": "tessaris",
                    "type": "goal_created",
                    "content": f"Goal '{goal.get('name')}' from glyph: {glyph}",
                    "data": goal
                })

    def _maybe_suggest_boot(self, glyph: str, branch: ThoughtBranch):
        if "Boot" in glyph or glyph.startswith("⟦ Skill") or glyph.startswith("⟦ Boot"):
            skill = self.boot_selector.find_matching_skill(glyph)
            if skill:
                print(f"[🚀] Matching boot skill: {skill['title']}")
                MEMORY.store({
                    "label": "tessaris_boot_proposal",
                    "role": "tessaris",
                    "type": "boot_skill",
                    "content": f"Proposed boot skill: {skill['title']} from glyph: {glyph}",
                    "data": skill
                })
            else:
                print("😕 No matching boot skill found.")


    def _coerce_reflection_text(self, value: Any) -> str:
        """
        Convert arbitrary input into safe readable reflection text.
        """
        try:
            if value is None:
                return ""

            if isinstance(value, str):
                return value.strip()

            if isinstance(value, dict):
                if "input" in value:
                    return str(value.get("input", "")).strip()
                if "signal" in value:
                    return str(value.get("signal", "")).strip()
                if "text" in value:
                    return str(value.get("text", "")).strip()
                return json.dumps(value, ensure_ascii=False, default=str)

            if isinstance(value, (list, tuple)):
                return json.dumps(list(value), ensure_ascii=False, default=str)

            return str(value).strip()
        except Exception:
            return str(value)

    def _parse_glyph(self, glyph: Any) -> Optional[dict]:
        """
        Parse canonical glyph syntax if present.

        Supported canonical form:
            ⟦ Type | Tag : Value -> Action ⟧

        Fail-open:
        - returns a structured plain-text packet for non-glyph inputs
        - never raises intentionally
        """
        try:
            if glyph is None:
                return None

            if isinstance(glyph, dict):
                return {
                    "type": "Input",
                    "tag": glyph.get("tag", "Structured"),
                    "value": self._coerce_reflection_text(glyph),
                    "action": glyph.get("action", "Reflect"),
                    "is_glyph": False,
                    "raw": glyph,
                }

            if not isinstance(glyph, str):
                return {
                    "type": "Input",
                    "tag": "NonString",
                    "value": self._coerce_reflection_text(glyph),
                    "action": "Reflect",
                    "is_glyph": False,
                    "raw": glyph,
                }

            text = glyph.strip()
            if not text:
                return None

            # Non-glyph plain language -> structured fallback, not an error
            if not (text.startswith("⟦") and text.endswith("⟧")):
                return {
                    "type": "Input",
                    "tag": "PlainText",
                    "value": text,
                    "action": "Reflect",
                    "is_glyph": False,
                    "raw": text,
                }

            inner = text[1:-1].strip("⟦⟧").strip()

            action = "Reflect"
            left = inner
            if "->" in inner:
                left, action = inner.split("->", 1)
                left = left.strip()
                action = action.strip() or "Reflect"

            if ":" not in left:
                return {
                    "type": "Glyph",
                    "tag": "Untitled",
                    "value": left.strip(),
                    "action": action,
                    "is_glyph": True,
                    "raw": text,
                }

            type_tag, value = left.split(":", 1)
            type_tag = type_tag.strip()
            value = value.strip()

            if "|" in type_tag:
                g_type, tag = type_tag.split("|", 1)
            else:
                g_type, tag = type_tag, "Untitled"

            return {
                "type": g_type.strip() or "Glyph",
                "tag": tag.strip() or "Untitled",
                "value": value,
                "action": action,
                "is_glyph": True,
                "raw": text,
            }

        except Exception as e:
            sci_emit("tessaris_error", f"{str(e)[:200]}")
            print(f"[⚠️] Glyph parse failed: {e}")

            try:
                return {
                    "type": "Input",
                    "tag": "Fallback",
                    "value": self._coerce_reflection_text(glyph),
                    "action": "Reflect",
                    "is_glyph": False,
                    "raw": glyph,
                }
            except Exception:
                return None

    def extract_intents_from_glyphs(self, glyphs, metadata=None):
        """
        Parse glyphs into actionable intents, generate resonant plans,
        and route through the Action Switch for execution.
        """
        for glyph in glyphs:
            parsed = self._parse_glyph(glyph)
            if not parsed:
                continue

            intent_type = None
            payload = {}

            if parsed["type"] == "Goal":
                intent_type = "goal"
                payload = {
                    "name": parsed.get("tag"),
                    "description": parsed.get("value"),
                }
            elif parsed["type"] in ["Skill", "Boot"]:
                intent_type = "avatar_action"
                payload = {
                    "skill": parsed.get("value"),
                    "reason": parsed.get("tag"),
                }
            elif parsed["type"] == "Plan":
                intent_type = "plan"
                payload = {
                    "steps": [parsed.get("value")],
                    "topic": parsed.get("tag"),
                }

            if intent_type:
                sci_emit("tessaris_action", f"Intent -> {intent_type} | {payload}")
                intent_data = {
                    "type": intent_type,
                    "data": payload,
                    "source": "tessaris_engine",
                    "glyph": glyph,
                    "metadata": metadata or {},
                }

                # 🧩 Log extracted intent (safe)
                _kg_log_safe(self.kg_writer, "intent_extracted", {
                    "intent_type": intent_type,
                    "glyph": glyph,
                    "payload": payload
                })

                # 🧭 Generate resonant plan and route through Action Switch
                try:
                    plan = self.strategy_planner.generate_plan(intent_data)
                    self.strategy_planner.adaptive_refinement()
                    self.strategy_planner.export_resonant_summary()

                    print(f"🧭 Generated resonant plan for intent: {intent_data.get('type')}")
                    # 💓 Reinforce based on planning success
                    self.update_resonance_feedback(outcome_score=0.8, reason="Plan generation success")
                    try:
                        self.action_switch.route(plan)
                    except Exception as route_err:
                        print(f"⚠️ ActionSwitch routing failed: {route_err}")

                except Exception as e:
                    sci_emit("tessaris_error", f"{str(e)[:200]}")
                    self.update_resonance_feedback(outcome_score=0.3, reason="Plan generation failure")
                    print(f"⚠️ Plan generation failed for intent: {e}")

                # 🧠 Always queue intent for downstream Aion/Tessaris executors
                queue_tessaris_intent(intent_data)
                print(f"🧠 Queued Tessaris intent ({intent_type}): {payload}")

    # ---- Compatibility shim: allow executor to call tessaris.interpret(...) ----
    def interpret_governed(self, instruction_tree, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Interpret a mission through the canonical proposal/authority boundary."""
        from backend.modules.hexcore.governed_cognitive_stack import GovernedCognitiveStack

        ctx = dict(context or {})
        mission = instruction_tree if isinstance(instruction_tree, dict) else {
            "objective": _summarize_tree(instruction_tree)
        }
        if isinstance(mission, dict):
            mission = {**mission, **ctx}
        return GovernedCognitiveStack().deliberate(mission)

    def interpret(self, instruction_tree, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute/interpret a Codex instruction tree.
        Tries existing methods if present; otherwise returns a shallow echo result.
        """
        ctx = context or {}
        if ctx.get("governed_mission") is True:
            return self.interpret_governed(instruction_tree, ctx)
        sci_emit("tessaris_start", f"Instruction -> {str(instruction_tree)[:240]}")

        # Prefer an existing concrete method if you already implemented one
        if hasattr(self, "execute") and callable(getattr(self, "execute")):
            sci_emit("tessaris_parse", json.dumps({"tree": instruction_tree}, ensure_ascii=False))
            try:
                result = self.execute(instruction_tree, ctx)
                sci_emit("tessaris_output", json.dumps({"result": result}, ensure_ascii=False))
                return result
            except Exception as e:
                sci_emit("tessaris_error", f"{str(e)[:200]}")
                return {"status": "error", "error": f"Tessaris.execute failed: {e}"}

        if hasattr(self, "run") and callable(getattr(self, "run")):
            sci_emit("tessaris_parse", json.dumps({"tree": instruction_tree}, ensure_ascii=False))
            try:
                result = self.run(instruction_tree, ctx)
                sci_emit("tessaris_output", json.dumps({"result": result}, ensure_ascii=False))
                return result
            except Exception as e:
                sci_emit("tessaris_error", f"{str(e)[:200]}")
                return {"status": "error", "error": f"Tessaris.run failed: {e}"}

        # Fallback: shallow interpretation (structure-only echo)
        try:
            fallback = {
                "status": "ok",
                "result": {
                    "op": "interpret",
                    "summary": _summarize_tree(instruction_tree),
                },
            }
            sci_emit("tessaris_output", json.dumps({"result": fallback}, ensure_ascii=False))
            return fallback
        except Exception as e:
            sci_emit("tessaris_error", f"{str(e)[:200]}")
            return {"status": "error", "error": f"Tessaris fallback failed: {e}"}

    def clear(self):
        self.active_branches = []
        self.active_thoughts = []

# keep this callable exactly like your existing uses: run_lean_self_rewrite(glyph)
def run_lean_self_rewrite(glyph: Any, *, context: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
    """
    Attempt to rewrite the given glyph using Lean tactic suggestion or axiom mutation.
    Used as fallback on contradiction or entropy spike.
    """
    from backend.modules.lean.lean_tactic_suggester import suggest_tactic_patch
    from backend.modules.lean.auto_mutate_axioms import mutate_axioms_for_glyph

    mutated: List[Dict[str, Any]] = []

    # Accept either dict-glyphs or string-glyphs without breaking legacy behavior
    meta = {}
    if isinstance(glyph, dict):
        meta = glyph.get("meta", {}) or {}

    if meta.get("leanProof"):
        try:
            suggestion = suggest_tactic_patch(glyph)
            if suggestion:
                mutated.append(suggestion)
        except Exception as e:
            sci_emit("tessaris_error", f"{str(e)[:200]}")
            print(f"⚠️ Lean tactic suggestion failed: {e}")

    try:
        axiom_mutations = mutate_axioms_for_glyph(glyph)
        mutated.extend(axiom_mutations)
    except Exception as e:
        sci_emit("tessaris_error", f"{str(e)[:200]}")
        print(f"⚠️ Axiom mutation failed: {e}")

    return mutated
