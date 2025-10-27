#!/usr/bin/env python3
"""
🎯 GoalTaskManager — Phase 55 Task 3
───────────────────────────────────────────────────────────────
Resonant-aware goal orchestration with tension detection and GSI feedback.

Upgrades:
  • Integrates ResonanceHeartbeat for continuous SQI feedback
  • Computes per-goal Goal Stability Index (GSI)
  • Detects and resolves resonance tension events
  • Logs to ResonantMemoryCache + broadcasts via WebSocket
  • Adapts goal priority using personality traits + entropy feedback
"""

import random
import logging
from datetime import datetime

# Core subsystems
from backend.modules.skills.goal_engine import GoalEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
Theta = ResonanceHeartbeat(namespace="global_theta")
# WebSocket optional
try:
    from backend.modules.websocket_manager import WebSocketManager
    WS = WebSocketManager()
except Exception:
    WS = None

# DNA switch registration
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

log = logging.getLogger(__name__)


class GoalTaskManager:
    def __init__(self):
        from backend.modules.skills.goal_engine import GoalEngine

        self.goal_engine = GoalEngine(
            enable_glyph_logging=True,
            goal_file="/workspaces/COMDEX/data/goals/goal_engine_data.json"
        )
        self.personality = PersonalityProfile()
        self.rmc = ResonantMemoryCache()

        # Active goal tracking
        self.active_goal = None
        self.last_gsi = 0.0
        self.tension_threshold = 0.25  # ΔGSI threshold for tension events

        # 💓 Resonance coupling
        self.heartbeat = ResonanceHeartbeat(namespace="goal_task_manager", base_interval=3.0)
        self.heartbeat.register_listener(self._on_heartbeat)
        self.heartbeat.start()

        log.info("💓 GoalTaskManager linked to Resonance Heartbeat + RMC.")

    # ------------------------------------------------------------
    def prioritize_goals(self):
        """
        Adjust goal priorities based on personality and recent resonance context.
        """
        traits = self.personality.get_profile()
        goals = self.goal_engine.get_all_goals() or []

        for goal in goals:
            base_priority = goal.get("priority", 1.0)
            name = goal.get("name", "").lower()

            # ✴️ Personality influence
            base_priority += 0.5 * traits.get("ambition", 0)
            if traits.get("curiosity", 0) > 0.6 and "learn" in name:
                base_priority += 1.0
            if traits.get("discipline", 0) < 0.4:
                base_priority -= 0.5

            # 🔄 Resonance memory influence
            mem = self.rmc.lookup(name)
            if mem and "stability" in mem:
                base_priority += mem["stability"] * 0.3

            goal["priority"] = max(0.1, round(base_priority, 2))

        return sorted(goals, key=lambda g: g["priority"], reverse=True)

    # ------------------------------------------------------------
    def compute_goal_stability_index(self, goal_name: str, sqi: float, entropy: float) -> float:
        """
        Compute GSI = SQI × (1 − entropy) to represent harmonic goal stability.
        """
        return round(max(0.0, min(1.0, sqi * (1.0 - entropy))), 4)

    # ------------------------------------------------------------
    def detect_tension_event(self, new_gsi: float):
        """
        Detects ΔGSI deviation and emits tension events accordingly.
        """
        delta = abs(new_gsi - self.last_gsi)
        if delta > self.tension_threshold:
            event_type = "tension_spike" if new_gsi < self.last_gsi else "tension_release"
            payload = {
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "ΔGSI": round(delta, 4),
                "previous": self.last_gsi,
                "current": new_gsi,
                "goal": self.active_goal
            }

            # Log + broadcast
            # Proper 4-arg call: rho, entropy, sqi, delta
            self.rmc.push_sample(
                rho=new_gsi,                # Resonant alignment
                entropy=abs(delta),         # Estimate entropy as magnitude of change
                sqi=new_gsi,                # Mirror GSI as SQI proxy
                delta=delta                 # Actual variation
            )
            self.rmc.save()
            if WS:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    coro = WS.broadcast(payload)
                    asyncio.ensure_future(coro) if loop.is_running() else loop.run_until_complete(coro)
                except Exception as e:
                    log.warning(f"[WS] Tension event broadcast failed: {e}")

            log.warning(f"[⚡] Resonance tension event: {payload}")
        self.last_gsi = new_gsi

    # ------------------------------------------------------------
    def _on_heartbeat(self, metrics: dict):
        """
        On each heartbeat, re-evaluate goal stability and update tension dynamics.
        """
        sqi = metrics.get("sqi", 0.5)
        entropy = metrics.get("Φ_entropy", 0.5)

        if not self.active_goal:
            goals = self.prioritize_goals()
            if goals:
                self.active_goal = goals[0]["name"]

        if self.active_goal:
            gsi = self.compute_goal_stability_index(self.active_goal, sqi, entropy)
            self.detect_tension_event(gsi)
            self.rmc.update_resonance_link(self.active_goal, "gsi", gsi)
            self.rmc.save()

            log.info(f"[Θ] Updated GSI for {self.active_goal} → {gsi:.3f}")

    # ------------------------------------------------------------
    def get_next_task(self):
        """
        Return the highest-priority active goal.
        """
        prioritized = self.prioritize_goals()
        if not prioritized:
            return None
        self.active_goal = prioritized[0]["name"]
        return prioritized[0]

    # ------------------------------------------------------------
    def check_resonance_alignment(self):
        """
        Compare per-goal SQI vs system mean and emit resonance_tension events
        when goals drift beyond harmonic stability.
        """
        try:
            goals = self.goal_engine.get_all_goals() or []
            if not goals:
                return

            mean_sqi = self.rmc.average_sqi()
            for g in goals:
                g_sqi = g.get("sqi", 0.5)
                delta = g_sqi - mean_sqi
                if abs(delta) > 0.15:
                    Theta.event("resonance_tension", goal=g.get("name"), delta=delta)
                    log.warning(f"[Θ] ⚡ Resonance tension detected: {g.get('name')} Δ={delta:+.3f}")
                    if hasattr(self, "dashboard"):
                        self.dashboard.log_event("resonance_tension", {"goal": g.get("name"), "delta": delta})
        except Exception as e:
            log.warning(f"[Θ] resonance alignment check failed: {e}")

    # ------------------------------------------------------------
    def run_next_task(self):
        """
        Execute the top goal with dynamic resonance modulation.
        """
        task = self.get_next_task()
        if not task:
            return {"status": "no_goals", "message": "No active goals found."}

        # Generate synthetic confidence based on GSI + traits
        traits = self.personality.get_profile()
        gsi_mem = self.rmc.lookup(task["name"])
        gsi_factor = gsi_mem.get("stability", 0.5) if gsi_mem else 0.5
        confidence = round(0.5 + 0.5 * (traits.get("discipline", 0.5) + gsi_factor) / 2, 2)

        result = {
            "goal": task["name"],
            "status": "in_progress",
            "priority": task["priority"],
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"🎯 Executing goal: {task['name']} (priority={task['priority']}, GSI≈{gsi_factor:.2f})"
        }

        # Log to RMC
        self.rmc.update_resonance_link(task["name"], "execution", confidence)
        self.rmc.save()
        self.check_resonance_alignment()

        log.info(result["message"])
        return result


# ------------------------------------------------------------
# Optional CLI test
# ------------------------------------------------------------
if __name__ == "__main__":
    mgr = GoalTaskManager()
    out = mgr.run_next_task()
    print(out)