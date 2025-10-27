#!/usr/bin/env python3
# ============================================================
# ⚙️ Tessaris Action Switch — P5 Routing Layer
# ============================================================
# Routes generated plans into execution pathways:
#   • HexCore StrategyEngine
#   • CodexExecutor (if symbolic execution required)
#   • AION reflective feedback
#   • ResonantHeartbeat coupling for adaptive weighting
# ============================================================

import time
import logging
from datetime import datetime
from backend.modules.hexcore.strategy_engine import StrategyEngine
from backend.modules.hexcore.prediction_engine import PredictionEngine
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.resonance.heartbeat import ResonanceHeartbeat

log = logging.getLogger(__name__)


class ActionSwitch:
    """
    Central execution router that receives generated plans (PlanTree or dict)
    and determines where to route them (HexCore, Codex, Aion feedback, etc.)
    """

    def __init__(self):
        self.strategy_engine = StrategyEngine()
        self.prediction_engine = PredictionEngine()
        self.rmc = ResonantMemoryCache()
        self.heartbeat = ResonanceHeartbeat(namespace="action_switch")
        self.heartbeat.register_listener(self._on_heartbeat)
        self.last_routed = None
        print("⚙️ ActionSwitch initialized and linked to Resonance Heartbeat.")

    # ------------------------------------------------------------
    def route(self, plan: dict):
        """
        Route a resonant plan to the appropriate execution module.
        """
        if not plan:
            log.warning("⚠️ No plan provided to ActionSwitch.route().")
            return

        goal = plan.get("goal", "undefined")
        resonance_score = plan.get("resonance_score", 0.0)
        deferred = plan.get("deferred", False)

        print(f"⚙️ [ActionSwitch] Routing plan → Goal: {goal} | Resonance: {resonance_score:.3f}")

        # 🧭 Step 1: Evaluate feasibility & prediction
        feasibility = self.prediction_engine.assess_feasibility(goal)
        print(f"🔮 Feasibility prediction: {feasibility:.2f}")

        # 🧠 Step 2: Store plan in Resonant Memory for traceability
        self.rmc.set("last_routed_plan", {
            "goal": goal,
            "timestamp": datetime.now().isoformat(),
            "resonance_score": resonance_score,
            "feasibility": feasibility,
        })

        # 🧩 Step 3: Route to StrategyEngine or defer
        if deferred or feasibility < 0.3:
            print(f"🕓 Plan deferred: {goal}")
            self._store_deferred(plan)
            return

        try:
            result = self.strategy_engine.execute_plan(plan)
            self.last_routed = plan
            print(f"✅ Executed plan via StrategyEngine: {goal}")
            return result
        except Exception as e:
            print(f"⚠️ ActionSwitch execution failed: {e}")
            self._store_deferred(plan)

    # ------------------------------------------------------------
    def notify_new_plan(self, path: str):
        """
        Called by StrategyPlanner.export_to_dc() after export.
        Simply logs and stores metadata for synchronization.
        """
        self.rmc.set("last_exported_plan_path", {
            "path": path,
            "timestamp": datetime.now().isoformat(),
        })
        print(f"📦 ActionSwitch notified of new plan export: {path}")

    # ------------------------------------------------------------
    def _store_deferred(self, plan):
        """
        Internal helper — store deferred plans into resonant cache.
        """
        try:
            deferred_plans = self.rmc.get("deferred_plans") or []
            deferred_plans.append({
                "goal": plan.get("goal"),
                "timestamp": datetime.now().isoformat(),
                "reason": "low_feasibility_or_manual_defer"
            })
            self.rmc.set("deferred_plans", deferred_plans)
            print(f"💤 Deferred plan stored: {plan.get('goal')}")
        except Exception as e:
            print(f"⚠️ Failed to store deferred plan: {e}")

    # ------------------------------------------------------------
    def _on_heartbeat(self, pulse_data: dict):
        """
        Called every Resonance Heartbeat tick — update plan weighting.
        """
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