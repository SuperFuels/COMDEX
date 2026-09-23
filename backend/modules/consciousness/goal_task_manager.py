#!/usr/bin/env python3
"""
🎯 GoalTaskManager - Phase 55 Task 3
───────────────────────────────────────────────────────────────
Resonant-aware goal orchestration with tension detection and GSI feedback.

Upgrades:
  * Integrates ResonanceHeartbeat for continuous SQI feedback
  * Computes per-goal Goal Stability Index (GSI)
  * Detects and resolves resonance tension events
  * Logs to ResonantMemoryCache + broadcasts via WebSocket
  * Adapts goal priority using personality traits + entropy feedback
  * Uses repo-local writable goal storage instead of hard-coded /workspaces paths
  * Fails open if optional subsystems are unavailable
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Optional

# Core subsystems
from backend.modules.skills.goal_engine import GoalEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

# Global Theta bus
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


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _repo_root() -> Path:
    # backend/modules/consciousness/goal_task_manager.py
    # parents[0] = consciousness
    # parents[1] = modules
    # parents[2] = backend
    # parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def _default_goal_file() -> Path:
    env_path = os.getenv("AION_GOAL_FILE")
    if env_path:
        return Path(env_path).expanduser().resolve()

    root = _repo_root()
    return root / "data" / "goals" / "goal_engine_data.json"


class GoalTaskManager:
    def __init__(self):
        goal_file = _default_goal_file()
        goal_file.parent.mkdir(parents=True, exist_ok=True)

        self.goal_engine = GoalEngine(
            enable_glyph_logging=True,
            goal_file=str(goal_file),
        )
        self.personality = PersonalityProfile()
        self.rmc = ResonantMemoryCache()

        # Active goal tracking
        self.active_goal: Optional[str] = None
        self.last_gsi: float = 0.0
        self.tension_threshold: float = 0.25  # ΔGSI threshold for tension events
        self.goal_file = goal_file

        # Optional dashboard hook
        self.dashboard = None

        # 💓 Resonance coupling
        self.heartbeat = ResonanceHeartbeat(namespace="goal_task_manager", base_interval=3.0)
        try:
            self.heartbeat.register_listener(self._on_heartbeat)
        except Exception as e:
            log.warning(f"[GoalTaskManager] heartbeat listener registration failed: {e}")

        try:
            self.heartbeat.start()
        except Exception as e:
            log.warning(f"[GoalTaskManager] heartbeat start failed: {e}")

        log.info(
            "💓 GoalTaskManager linked to Resonance Heartbeat + RMC. goal_file=%s",
            self.goal_file,
        )

    # ------------------------------------------------------------
    def prioritize_goals(self):
        """
        Prioritize authorized goals using deadlines, dependencies, verified
        outcomes and capability gaps. Personality and resonance cannot create
        or materially reorder objectives.
        """
        try:
            goals = self.goal_engine.get_all_goals() or []
        except Exception as e:
            log.warning(f"[GoalTaskManager] failed to fetch goals: {e}")
            goals = []

        for goal in goals:
            base_priority = _safe_float(goal.get("priority", 1.0), 1.0)
            name = str(goal.get("name", "")).strip().lower()

            if goal.get("owner_authorized") or goal.get("approval_policy") in {
                "autonomous_allowed", "human_approved"
            }:
                base_priority += 1.0
            if goal.get("deadline") or goal.get("next_outcome_due"):
                base_priority += 0.6
            if goal.get("blocks_other_goals"):
                base_priority += 0.5
            if goal.get("capability_gap"):
                base_priority += 0.35
            if goal.get("status") in {"blocked", "waiting_authority"}:
                base_priority -= 0.75
            if goal.get("verified_progress") is False:
                base_priority -= 0.25

            goal["priority"] = max(0.1, round(base_priority, 2))
            goal["priority_authority"] = "goal_contract_and_verified_outcomes"

        return sorted(goals, key=lambda g: _safe_float(g.get("priority", 0.0), 0.0), reverse=True)

    # ------------------------------------------------------------
    def compute_goal_stability_index(self, goal_name: str, sqi: float, entropy: float) -> float:
        """
        Compute GSI = SQI * (1 - entropy) to represent harmonic goal stability.
        """
        _ = goal_name  # reserved for future goal-specific shaping
        sqi_n = max(0.0, min(1.0, _safe_float(sqi, 0.5)))
        entropy_n = max(0.0, min(1.0, _safe_float(entropy, 0.5)))
        return round(max(0.0, min(1.0, sqi_n * (1.0 - entropy_n))), 4)

    # ------------------------------------------------------------
    def _broadcast_payload(self, payload: dict[str, Any]) -> None:
        if WS is None:
            return

        try:
            coro = WS.broadcast(payload)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
            except RuntimeError:
                asyncio.run(coro)
        except Exception as e:
            log.warning(f"[WS] broadcast failed: {e}")

    # ------------------------------------------------------------
    def detect_tension_event(self, new_gsi: float):
        """
        Detects ΔGSI deviation and emits tension events accordingly.
        """
        new_gsi = max(0.0, min(1.0, _safe_float(new_gsi, 0.0)))
        delta = abs(new_gsi - self.last_gsi)

        if delta > self.tension_threshold:
            event_type = "tension_spike" if new_gsi < self.last_gsi else "tension_release"
            payload = {
                "event": event_type,
                "timestamp": _utc_now_iso(),
                "delta_gsi": round(delta, 4),
                "previous": self.last_gsi,
                "current": new_gsi,
                "goal": self.active_goal,
            }

            try:
                self.rmc.push_sample(
                    rho=new_gsi,
                    entropy=delta,
                    sqi=new_gsi,
                    delta=delta,
                )
                self.rmc.save()
            except Exception as e:
                log.warning(f"[GoalTaskManager] RMC push_sample/save failed: {e}")

            self._broadcast_payload(payload)
            log.warning(f"[⚡] Resonance tension event: {payload}")

        self.last_gsi = new_gsi

    # ------------------------------------------------------------
    def _on_heartbeat(self, metrics: dict):
        """
        On each heartbeat, re-evaluate goal stability and update tension dynamics.
        """
        if not isinstance(metrics, dict):
            metrics = {}

        sqi = _safe_float(metrics.get("sqi", 0.5), 0.5)
        entropy = _safe_float(metrics.get("Φ_entropy", metrics.get("phi_entropy", 0.5)), 0.5)

        if not self.active_goal:
            goals = self.prioritize_goals()
            if goals:
                self.active_goal = str(goals[0].get("name", "")).strip() or None

        if self.active_goal:
            gsi = self.compute_goal_stability_index(self.active_goal, sqi, entropy)
            self.detect_tension_event(gsi)

            try:
                self.rmc.update_resonance_link(self.active_goal, "gsi", gsi)
                self.rmc.save()
            except Exception as e:
                log.warning(f"[GoalTaskManager] RMC update/save failed for {self.active_goal}: {e}")

            log.info(f"[Θ] Updated GSI for {self.active_goal} -> {gsi:.3f}")

    # ------------------------------------------------------------
    def get_next_task(self):
        """
        Return the highest-priority active goal.
        """
        prioritized = self.prioritize_goals()
        if not prioritized:
            self.active_goal = None
            return None

        self.active_goal = str(prioritized[0].get("name", "")).strip() or None
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

            mean_sqi = _safe_float(self.rmc.average_sqi(), 0.5)

            for g in goals:
                goal_name = g.get("name")
                g_sqi = _safe_float(g.get("sqi", 0.5), 0.5)
                delta = g_sqi - mean_sqi

                if abs(delta) > 0.15:
                    try:
                        Theta.event("resonance_tension", goal=goal_name, delta=delta)
                    except Exception as e:
                        log.warning(f"[Θ] event emit failed for {goal_name}: {e}")

                    log.warning(f"[Θ] ⚡ Resonance tension detected: {goal_name} Δ={delta:+.3f}")

                    if self.dashboard is not None:
                        try:
                            self.dashboard.log_event(
                                "resonance_tension",
                                {"goal": goal_name, "delta": delta},
                            )
                        except Exception as e:
                            log.warning(f"[Θ] dashboard log_event failed: {e}")

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

        try:
            traits = self.personality.get_profile() or {}
        except Exception as e:
            log.warning(f"[GoalTaskManager] personality profile unavailable during run_next_task: {e}")
            traits = {}

        try:
            gsi_mem = self.rmc.lookup(task["name"])
        except Exception as e:
            log.warning(f"[GoalTaskManager] RMC lookup failed during run_next_task: {e}")
            gsi_mem = None

        gsi_factor = _safe_float(gsi_mem.get("stability", 0.5), 0.5) if isinstance(gsi_mem, dict) else 0.5
        discipline = _safe_float(traits.get("discipline", 0.5), 0.5)
        confidence = round(0.5 + 0.5 * ((discipline + gsi_factor) / 2.0), 2)

        result = {
            "goal": task["name"],
            "status": "in_progress",
            "priority": _safe_float(task.get("priority", 1.0), 1.0),
            "confidence": confidence,
            "timestamp": _utc_now_iso(),
            "message": (
                f"🎯 Executing goal: {task['name']} "
                f"(priority={_safe_float(task.get('priority', 1.0), 1.0)}, GSI≈{gsi_factor:.2f})"
            ),
        }

        try:
            self.rmc.update_resonance_link(task["name"], "execution", confidence)
            self.rmc.save()
        except Exception as e:
            log.warning(f"[GoalTaskManager] execution RMC update/save failed: {e}")

        self.check_resonance_alignment()
        log.info(result["message"])
        return result


# ------------------------------------------------------------
# Optional CLI test
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mgr = GoalTaskManager()
    out = mgr.run_next_task()
    print(out)
