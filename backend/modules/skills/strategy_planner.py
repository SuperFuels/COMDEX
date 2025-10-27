#!/usr/bin/env python3
"""
🧭 StrategyPlanner — Phase 55 Resonant Upgrade + Goal Cluster Bridge
─────────────────────────────────────────────────────────────────────
Extends strategic reasoning with Θ-feedback, resonance scoring,
and adaptive goal-cluster coupling.

Core Upgrades:
  • SQI evaluation for each generated plan
  • Continuous Θ-feedback via ResonanceHeartbeat
  • Predictive refinement and adaptive weighting
  • ResonantMemoryCache (RMC) harmonic persistence
  • Automatic goal-cluster creation / reinforcement (P55 T4)
  • Bidirectional GSI⇄SQI resonance exchange
"""

import uuid
import time
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 🔧 Core Dependencies
# ─────────────────────────────────────────────────────────────
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.consciousness.prediction_engine import PredictionEngine
from backend.modules.hexcore.strategy_engine import StrategyEngine
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

# 🌐 Global Θ-field instance for unified resonance events
Theta = ResonanceHeartbeat(namespace="global_theta")

# 🔗 Dynamic bridge to Goal Task Manager – loaded lazily
GOAL_CLUSTER = None
def get_goal_cluster():
    """
    Returns a singleton GoalTaskManager using the unified persistent goal file.
    Ensures StrategyPlanner ↔ GoalTaskManager ↔ GoalEngine share same storage.
    """
    global GOAL_CLUSTER
    if GOAL_CLUSTER is None:
        from backend.modules.consciousness.goal_task_manager import GoalTaskManager
        from backend.modules.skills.goal_engine import GoalEngine
        GOAL_PATH = "/workspaces/COMDEX/data/goals/goal_engine_data.json"

        # Ensure the same file is used across all systems
        mgr = GoalTaskManager()
        mgr.goal_engine = GoalEngine(goal_file=GOAL_PATH)
        GOAL_CLUSTER = mgr

    return GOAL_CLUSTER

DNA_SWITCH.register(__file__)
log = logging.getLogger(__name__)
STRATEGY_FILE = Path("data/memory/aion_strategies.json")


# ============================================================
# 🧠 Base Resonant Strategy Planner
# ============================================================
class StrategyPlanner:
    """Resonant Strategy Planner — Base Layer for Phase 55."""

    def __init__(self, enable_glyph_logging: bool = True):
        self.enable_glyph_logging = enable_glyph_logging
        self.memory = MemoryEngine()
        self.prediction_engine = PredictionEngine()
        self.strategy_engine = StrategyEngine()
        self.rmc = ResonantMemoryCache()
        self.strategies = []

        # 💓 Resonant coupling
        self.heartbeat = ResonanceHeartbeat(namespace="strategy_planner")
        self.heartbeat.register_listener(self._on_heartbeat)
        self.load()
        log.info("💓 StrategyPlanner linked to Resonance Heartbeat.")

    # ------------------------------------------------------------
    def plan_strategy(self, goal_name: str):
        """Generate and evaluate a symbolic plan for a given goal."""
        steps = [
            f"Analyze context for {goal_name}",
            f"Identify subgoals for {goal_name}",
            f"Simulate actions for {goal_name}",
            f"Execute optimized sequence for {goal_name}",
            "Reflect and update resonance links",
        ]
        plan = {
            "id": str(uuid.uuid4()),
            "goal": goal_name,
            "steps": steps,
            "created_at": datetime.utcnow().isoformat(),
        }

        plan["resonance_score"] = self._evaluate_plan_resonance(plan)
        plan["timestamp"] = time.time()

        pred = self.prediction_engine.forecast(goal_name)
        plan["predicted_confidence"] = pred.get("confidence", 0.5)
        plan["predicted_outcome"] = pred.get("summary", "No prediction available")

        self.strategies.append(plan)
        self.save()
        self.rmc.update_resonance_link(goal_name, "plan", plan["resonance_score"])
        self.rmc.save()

        log.info(
            f"🎯 Plan generated → SQI={plan['resonance_score']:.3f}, "
            f"confidence={plan['predicted_confidence']:.3f}"
        )
        return plan

    # ------------------------------------------------------------
    def _evaluate_plan_resonance(self, plan):
        """Compute semantic–resonant alignment (SQI) of plan steps."""
        total, count = 0.0, 0
        for step in plan.get("steps", []):
            entry = self.rmc.lookup(step)
            if entry and "stability" in entry:
                total += entry["stability"]
                count += 1
        return round(total / max(count, 1), 3)

    # ------------------------------------------------------------
    def evaluate_plan(self, plan):
        """Emit Θ-resonant evaluation metrics for the given plan (Phase 55 T1)."""
        try:
            sqi = self._evaluate_plan_resonance(plan)
            entropy = 1.0 - sqi  # fallback proxy if no explicit entropy calc
            Theta.event("plan_eval", sqi=sqi, entropy=entropy, engine="StrategyPlanner")
            log.info(f"[Θ] event plan_eval SQI={sqi:.3f}, entropy={entropy:.3f}")
            if hasattr(self, "dashboard"):
                self.dashboard.log_event("plan_eval", {"SQI": sqi, "entropy": entropy})
            return sqi
        except Exception as e:
            log.warning(f"[Θ] evaluate_plan error: {e}")
            return 0.0

    # ------------------------------------------------------------
    def _on_heartbeat(self, metrics: dict):
        """Θ-pulse feedback loop for resonant weight adaptation."""
        try:
            drift = metrics.get("resonance_drift", 0.0)
            sqi = metrics.get("sqi", 0.0)
            stability = metrics.get("stability", 0.0)
            if not self.strategies:
                return
            for strat in self.strategies:
                old = strat.get("resonance_score", 0.5)
                adj = (sqi * 0.3 + stability * 0.2 - drift * 0.1)
                strat["resonance_score"] = max(0.0, min(1.0, old + adj))
            self.save()
            log.info(f"[Θ] ♻ Updated {len(self.strategies)} strategies with resonance feedback.")
        except Exception as e:
            log.warning(f"[Θ] Feedback error: {e}")

    # ------------------------------------------------------------
    def adaptive_refinement(self):
        """Auto-refine low-SQI strategies based on predictive confidence."""
        updated = 0
        for s in self.strategies:
            if s.get("resonance_score", 0.5) < 0.4:
                pred = self.prediction_engine.forecast(s["goal"])
                s["predicted_outcome"] = pred.get("summary", "")
                s["resonance_score"] = round(
                    (s.get("resonance_score", 0.5) + pred.get("confidence", 0.5)) / 2, 3
                )
                updated += 1
        if updated:
            self.save()
            log.info(f"🔁 Refined {updated} strategies with low resonance.")

    # ------------------------------------------------------------
    def load(self):
        if STRATEGY_FILE.exists():
            try:
                with open(STRATEGY_FILE, "r") as f:
                    self.strategies = json.load(f)
            except Exception as e:
                log.warning(f"⚠️ Failed to load strategies: {e}")
                self.strategies = []
        else:
            self.strategies = []

    def save(self):
        STRATEGY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STRATEGY_FILE, "w") as f:
            json.dump(self.strategies, f, indent=2)

    def export_summary(self, path="data/analysis/resonant_strategy_summary.json"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "goal": s.get("goal"),
                "resonance_score": s.get("resonance_score", 0.0),
                "predicted_confidence": s.get("predicted_confidence", 0.0),
                "timestamp": s.get("timestamp"),
            }
            for s in self.strategies
        ]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        log.info(f"📤 Exported resonant summary → {path}")


# ============================================================
# 🧭 P4 — Advanced Resonant Strategy Planner (Cluster Edition)
# ============================================================
class ResonantStrategyPlanner(StrategyPlanner):
    """
    Integrates predictive planning + goal cluster bridge for resonant coherence.
    """

    def __init__(self, enable_glyph_logging=True):
        super().__init__(enable_glyph_logging=enable_glyph_logging)
        from backend.modules.skills.goal_engine import GoalEngine
        self.goal_engine = GoalEngine(goal_file="/workspaces/COMDEX/data/goals/goal_engine_data.json")
        self.heartbeat = ResonanceHeartbeat(namespace="strategy_planner")
        self.heartbeat.register_listener(self._on_heartbeat)
        log.info("💓 ResonantStrategyPlanner initialized.")

    # ------------------------------------------------------------
    def generate_plan(self, intent: dict | str):
        """Build and evaluate a PlanTree from ReasonedIntent and sync goals."""
        goal = intent.get("what", intent) if isinstance(intent, dict) else str(intent)
        log.info(f"[P4] Generating resonant plan for intent: {goal}")

        plan = self.plan_strategy(goal)
        sqi_score = self._evaluate_plan_resonance(plan)
        plan["resonance_score"] = sqi_score
        plan["timestamp"] = time.time()

        pred = self.prediction_engine.forecast(goal)
        plan["predicted_outcome"] = pred.get("summary", "No prediction available")
        plan["predicted_confidence"] = pred.get("confidence", 0.5)
        self.rmc.update_resonance_link(goal, "plan", sqi_score)
        self.rmc.save()

        # ──────────────────────────────────────────────
        # 🌀 Resonant Goal Cluster Bridge (Phase 55 Task 4 – Stabilized)
        # ──────────────────────────────────────────────
        try:
            cluster = get_goal_cluster()

            # Detect early-cache conditions safely
            cache_data = getattr(self.rmc, "cache", {})
            cache_size = len(cache_data) if isinstance(cache_data, dict) else 0
            early_stage = cache_size < 50

            # 🌌 Normalize and bootstrap SQI
            normalized_sqi = sqi_score
            if early_stage or sqi_score < 0.7:
                normalized_sqi = round(0.75 + sqi_score * 0.25, 3)
                log.info(
                    f"[ClusterBridge] ⚛ Bootstrap normalization applied — SQI {sqi_score:.3f} → {normalized_sqi:.3f} "
                    f"(cache={cache_size})"
                )

            # Force creation for early phase testing
            if normalized_sqi >= 0.1 or early_stage:
                goals = cluster.goal_engine.get_all_goals()
                related = [g for g in goals if goal in g["name"] or g["name"] in goal]

                if not related:
                    new_goal = {
                        "name": f"cluster_goal_{goal.replace(' ', '_')}",
                        "description": f"Resonant cluster goal auto-derived from '{goal}'.",
                        "reward": 6,
                        "priority": round(max(normalized_sqi * 10, 5), 2),
                        "dependencies": [],
                        "created_at": datetime.utcnow().isoformat(),
                        "origin_strategy_id": plan.get("id", "unknown"),
                        "tags": ["cluster", "resonant", "auto", "bootstrap"],
                    }
                    cluster.goal_engine.assign_goal(new_goal)
                    log.info(f"[ClusterBridge] 🌱 Created goal cluster: {new_goal['name']}")
                else:
                    for g in related:
                        old = g.get("priority", 1.0)
                        g["priority"] = round(old + (normalized_sqi * 2), 2)
                        log.info(
                            f"[ClusterBridge] 🔁 Reinforced {g['name']} priority {old:.2f}→{g['priority']:.2f}"
                        )
                    cluster.goal_engine.save_goals()
            else:
                # Force creation if no goals exist (testing bootstrap)
                if not goals:
                    log.warning("⚠️ Planner GoalEngine has no cluster goals yet — bootstrapping one for test phase.")
                    new_goal = {
                        "name": f"cluster_goal_{goal.replace(' ', '_')}",
                        "description": f"[AutoTest] Bootstrap goal for '{goal}'",
                        "reward": 5,
                        "priority": round(normalized_sqi * 10, 2),
                        "dependencies": [],
                        "created_at": datetime.utcnow().isoformat(),
                        "origin_strategy_id": plan.get("id", "bootstrap"),
                        "tags": ["cluster", "resonant", "autogen", "test"],
                    }
                    cluster.goal_engine.assign_goal(new_goal)
                    cluster.goal_engine.save_goals()
                    log.info(f"[ClusterBridge] 🌱 Bootstrap cluster goal created → {new_goal['name']}")
                else:
                    log.info(f"[ClusterBridge] ⏸ Skipped cluster creation (SQI={normalized_sqi:.3f})")

        except Exception as e:
            log.warning(f"[ClusterBridge] ⚠ Resonant bridge error: {e}")

        # 🔁 Bidirectional coupling — boost plan from goal resonance (GSI)
        try:
            cluster = get_goal_cluster()
            gsi_avg = getattr(cluster, "latest_gsi", 0.5)
            plan["resonance_score"] = round((plan["resonance_score"] + gsi_avg) / 2, 3)
        except Exception:
            pass

        log.info(
            f"[P4] ✅ Plan generated → SQI={sqi_score:.3f}, "
            f"confidence={plan['predicted_confidence']:.3f}"
        )
        return plan

    # ------------------------------------------------------------
    def export_resonant_summary(self, path="data/analysis/resonant_strategy_summary.json"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "goal": s.get("goal"),
                "resonance_score": s.get("resonance_score", 0.0),
                "predicted_confidence": s.get("predicted_confidence", 0.0),
                "timestamp": s.get("timestamp"),
            }
            for s in self.strategies
        ]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        log.info(f"[P4] 📤 Exported resonant summary → {path}")


# ============================================================
# 🔗 Export API
# ============================================================
__all__ = ["StrategyPlanner", "ResonantStrategyPlanner"]