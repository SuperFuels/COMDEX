#!/usr/bin/env python3
# ================================================================
# ⚙️ Tessaris ActionSwitch - Reflex Routing Core (P5 + R4-R6 Integrated)
# ================================================================
# Combines high-level plan routing with deep reflex reasoning:
#   * HexCore Strategy + Prediction routing
#   * AION Reflex cognition (RuleBooks, Violations, ReflexMemory)
#   * ResonantHeartbeat Θ coupling for live adjustment
#   * Teleport/GWave traversal across rule domains
# ================================================================

import time, json, logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# ─────────── Legacy P5 components ───────────
from backend.modules.hexcore.strategy_engine import StrategyEngine
from backend.modules.consciousness.prediction_engine import PredictionEngine
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

# ─────────── Reflex R4-R6 components ───────────
from backend.modules.aion_cognition.cognitive_intent_loop import CognitiveIntentLoop
from backend.modules.aion_cognition.rulebook_streamer import RuleBookStreamer
from backend.modules.aion_cognition.violation_logger import ViolationLogger
from backend.modules.aion_cognition.rule_feedback_engine import RuleFeedbackEngine
from backend.modules.aion_cognition.rulebook_index import RuleBookIndex
from backend.modules.aion_cognition.reflex_memory import ReflexMemory

log = logging.getLogger(__name__)
OUT = Path("data/telemetry/action_switch_trace.json")

class ActionSwitch:
    """
    Central execution router that merges plan routing (P5)
    with symbolic reflex cognition (R4-R6).
    """

    def __init__(self, tau_theta: float = 0.35, *, repo_root: Path | None = None,
                 competency_gate: bool = True):
        # ⛓ P5 routing layer
        self.strategy_engine = StrategyEngine()
        self.prediction_engine = PredictionEngine()
        self.rmc = ResonantMemoryCache()
        self.heartbeat = ResonanceHeartbeat(namespace="action_switch")
        self.heartbeat.register_listener(self._on_heartbeat)

        # 🧠 Reflex layer
        self.intent_loop = CognitiveIntentLoop(tau=tau_theta)
        self.streamer = RuleBookStreamer()
        self.vlog = ViolationLogger()
        self.feedback = RuleFeedbackEngine()
        self.rule_index = RuleBookIndex()
        self.reflex = ReflexMemory()

        # Mission -> knowledge -> action binding. This remains a conservative
        # readiness gate in front of the original resonant/reflex execution
        # design; it does not replace StrategyEngine or reflex rules.
        self.capability_harness = None
        if competency_gate:
            try:
                from backend.modules.hexcore.mission_capability_action_harness import (
                    MissionCapabilityActionHarness,
                )
                self.capability_harness = MissionCapabilityActionHarness(
                    repo_root=(repo_root or Path.cwd()),
                )
            except Exception as error:
                log.warning("Capability harness unavailable; action remains proposal-only: %s", error)

        self.last_routed = None
        print("⚙️ ActionSwitch initialized (P5+R6) - Reflex Beam online and Θ-linked.")

    # ============================================================
    # 🔁 PLAN ROUTING (P5)
    # ============================================================
    def route(self, plan: dict):
        """Route a resonant plan to the appropriate execution module."""
        if not plan:
            log.warning("⚠️ No plan provided to ActionSwitch.route().")
            return

        goal = plan.get("goal", "undefined")
        resonance_score = plan.get("resonance_score", 0.0)
        deferred = plan.get("deferred", False)

        capability_decision = None
        if self.capability_harness is not None and not plan.get("skip_competency_gate"):
            capability_decision = self.capability_harness.evaluate(plan, register_learning=True)
            plan["capability_decision"] = capability_decision
            self.rmc.set("last_capability_decision", capability_decision)
            if capability_decision["decision"] in {"learn_then_execute", "clarify"}:
                reason = capability_decision["reason"]
                print(f"📚 Plan paused for capability acquisition: {goal} ({reason})")
                self._store_deferred(plan, reason=reason)
                return {"status": capability_decision["decision"],
                        "goal": goal, "capability_decision": capability_decision}

        print(f"⚙️ [ActionSwitch] Routing plan -> Goal: {goal} | Resonance: {resonance_score:.3f}")
        feasibility = self.prediction_engine.assess_feasibility({
            **plan,
            "objective": plan.get("objective") or goal,
            "capability_decision": capability_decision or plan.get("capability_decision"),
        })
        print(f"🔮 Feasibility prediction: {feasibility:.2f}")

        self.rmc.set("last_routed_plan", {
            "goal": goal,
            "timestamp": datetime.now().isoformat(),
            "resonance_score": resonance_score,
            "feasibility": feasibility,
        })

        if deferred or feasibility < 0.3:
            print(f"🕓 Plan deferred: {goal}")
            self._store_deferred(plan)
            return

        try:
            result = self.strategy_engine.execute_plan(
                plan, execution_adapter=plan.get("execution_adapter")
            )
            self.last_routed = plan
            if result.get("status") == "verified":
                print(f"✅ Verified plan outcome via StrategyEngine: {goal}")
            else:
                print(f"🧭 Plan remains proposal-only: {goal} ({result.get('status')})")
            return result
        except Exception as e:
            print(f"⚠️ ActionSwitch execution failed: {e}")
            self._store_deferred(plan)

    # ============================================================
    # 🧠 REFLEX EXECUTION (R4-R6)
    # ============================================================
    def _tick_theta(self, resonance: Dict[str, float], memory_stats: Dict[str, float], drift: float = 0.0):
        rho = float(resonance.get("ρ", 0.0))
        sqi = float(resonance.get("SQI", 0.0))
        act, theta = self.intent_loop.tick(rho=rho, drift=drift, memory_stats=memory_stats, sqi=sqi)
        return act, theta

    def current_action(self):
        """Return the currently active or last executed action for snapshot context."""
        try:
            return getattr(self, "active_action", None) or {"state": "idle"}
        except Exception:
            return {"state": "unknown"}

    def _teleport(self, domain: str):
        log.info(f"[Teleport] Jumping to rulebook domain: {domain}")
        self.rule_index.increment_usage(domain)

    def execute_reflex(self, action: str, context: Dict[str, Any], rule_context: Dict[str, Any], telemetry: Dict[str, Any]):
        """
        Reflex-level execution: evaluates rules, violations, mutations.
        """
        resonance = telemetry.get("resonance", {})
        memory_stats = telemetry.get("memory_stats", {})
        drift = float(telemetry.get("drift", 0.0))
        act, theta = self._tick_theta(resonance, memory_stats, drift)

        domain = rule_context.get("domain", "python_core")
        self._teleport(domain)

        rule_atoms = self.streamer.stream(action=action, context=rule_context)
        violations = [atom for atom in rule_atoms if atom.get("violated")]

        if violations:
            self.vlog.record(action, context, violations)
            mutation = self.feedback.suggest_mutation(action, context, violations)
            decision = {"allowed": False, "theta": theta, "mutation": mutation, "violations": violations}
            self.rule_index.record_mutation(domain, {"violations": len(violations), "mutation": mutation})
        else:
            decision = {"allowed": True, "theta": theta, "violations": []}

        # Reflex memory record
        outcome = {"success": decision["allowed"], "streamed_atoms": len(rule_atoms)}
        self.reflex.record(action, context, decision, outcome)

        # Telemetry trace
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT, "a") as f:
            f.write(json.dumps({
                "timestamp": time.time(),
                "action": action,
                "context": context,
                "rule_context": rule_context,
                "theta": theta,
                "allowed": decision["allowed"],
                "violations": len(violations),
            }) + "\n")

        log.info(f"[ActionSwitch] Reflex exec: {action} Θ={theta:.3f} allowed={decision['allowed']}")
        return decision, rule_atoms

    # ============================================================
    # 🧩 Synchronization + Deferred Plans
    # ============================================================
    def _store_deferred(self, plan, *, reason: str = "low_feasibility_or_manual_defer"):
        """Internal helper - store deferred plans into resonant cache."""
        try:
            deferred_plans = self.rmc.get("deferred_plans") or []
            deferred_plans.append({
                "goal": plan.get("goal"),
                "timestamp": datetime.now().isoformat(),
                "reason": reason
            })
            self.rmc.set("deferred_plans", deferred_plans)
            print(f"💤 Deferred plan stored: {plan.get('goal')}")
        except Exception as e:
            print(f"⚠️ Failed to store deferred plan: {e}")

    def pause_all(self):
        """Temporarily pause all ongoing action threads or beams."""
        self.active = False
        self.log.info("[ActionSwitch] ⚙️ All actions paused (manual override).")

    def resume_all(self):
        """Resume action execution after override release."""
        self.active = True
        self.log.info("[ActionSwitch] ⚙️ All actions resumed post-override.")    
    
    def log(self, msg: str, level: str = "info"):
        import logging
        getattr(logging, level, logging.info)(f"[ActionSwitch] {msg}")

    # ============================================================
    # 💓 Resonance Coupling (Θ-feedback)
    # ============================================================
    def _on_heartbeat(self, pulse_data: dict):
        """Called every Resonance Heartbeat tick - update active plan weighting."""
        delta = pulse_data.get("resonance_delta", 0.0)
        entropy = pulse_data.get("entropy", 0.0)

        try:
            if self.last_routed:
                score = self.last_routed.get("resonance_score", 0.0)
                updated_score = max(0.0, min(1.0, score + delta - (entropy * 0.1)))
                self.last_routed["resonance_score"] = updated_score
                self.rmc.set("last_routed_plan", self.last_routed)
                print(f"💓 Updated resonance score for active plan: {updated_score:.3f}")
        except Exception as e:
            print(f"⚠️ Heartbeat update failed in ActionSwitch: {e}")

    # ============================================================
    def notify_new_plan(self, path: str):
        """Called by StrategyPlanner.export_to_dc() after export."""
        self.rmc.set("last_exported_plan_path", {
            "path": path,
            "timestamp": datetime.now().isoformat(),
        })
        print(f"📦 ActionSwitch notified of new plan export: {path}")
