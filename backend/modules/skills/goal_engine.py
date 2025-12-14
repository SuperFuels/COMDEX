#!/usr/bin/env python3
"""
🎯 GoalEngine - Phase 55 Resonant Convergence Edition (Unified)
──────────────────────────────────────────────────────────────
Integrates goals, awareness traces, and milestones with:
  * Resonant Memory Cache (RMC) coupling
  * GSI-weighted prioritization
  * Tessaris + Photon Language triggers
  * Auto-healing persistence + entropy decay
  * Knowledge-Graph + WebSocket broadcasting
  * Shared persistence across StrategyPlanner + GoalTaskManager

IMPORTANT (Dev sanity):
  - This module MUST NOT start background heartbeat loops on import by default.
  - Enable resonance/heartbeat explicitly via env vars:
      GLYPH_GOAL_ENGINE_RESONANCE=1          # enable resonance subsystem
      GLYPH_GOAL_ENGINE_AUTOSTART=1          # auto-start heartbeat on init
      GLYPH_GOAL_ENGINE_BROADCAST=1          # allow websocket broadcast
"""

from __future__ import annotations

import os
import json
import time
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import GLYPH_API_BASE_URL, ENABLE_GLYPH_LOGGING
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

DNA_SWITCH.register(__file__)
log = logging.getLogger(__name__)

# --------------------------------------------------------------------
# Delayed imports to avoid circular deps / heavy imports at module load
# --------------------------------------------------------------------
def trigger_tessaris_from_goal(*a, **kw):
    from backend.modules.tessaris.tessaris_trigger import (
        trigger_tessaris_from_goal as _t,
    )
    return _t(*a, **kw)


# 🔗 Knowledge Graph writer singleton
_kg_writer = None


def get_goal_engine_kg_writer():
    global _kg_writer
    if _kg_writer is None:
        from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

        _kg_writer = get_kg_writer()
    return _kg_writer


# ============================================================
# ⚙️ Persistent Paths (Unified)
# ============================================================
DEFAULT_GOAL_FILE = Path(
    os.getenv("GLYPH_GOAL_FILE", "/workspaces/COMDEX/data/goals/goal_engine_data.json")
)
DEFAULT_LOG_FILE = Path(
    os.getenv("GLYPH_GOAL_LOG_FILE", "/workspaces/COMDEX/data/goals/goal_skill_log.json")
)
DEFAULT_GOAL_FILE.parent.mkdir(parents=True, exist_ok=True)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# ⚙️ Core Goal Engine
# ============================================================
class GoalEngine:
    """
    Goal engine with optional resonance heartbeat loop.

    By default (in uvicorn / dev servers), resonance is OFF unless:
      GLYPH_GOAL_ENGINE_RESONANCE=1

    Even if resonance is enabled, heartbeat autostart is OFF unless:
      GLYPH_GOAL_ENGINE_AUTOSTART=1
    """

    def __init__(
        self,
        enable_glyph_logging: bool = ENABLE_GLYPH_LOGGING,
        goal_file: Optional[str | Path] = None,
        *,
        resonance_enabled: Optional[bool] = None,
        autostart_resonance: Optional[bool] = None,
        broadcast_enabled: Optional[bool] = None,
    ):
        self.enable_glyph_logging = bool(enable_glyph_logging)

        self.goal_file = Path(goal_file) if goal_file else DEFAULT_GOAL_FILE
        self.log_file = self.goal_file.parent / DEFAULT_LOG_FILE.name

        self.goal_file.parent.mkdir(parents=True, exist_ok=True)

        # internal state
        self.goals: List[Dict[str, Any]] = []
        self.completed: List[str] = []
        self.log: List[Dict[str, Any]] = []
        self.agents: List[Any] = []

        # persistence load
        self.load_goals()
        self.load_log()

        # resonance toggles
        env_res = os.getenv("GLYPH_GOAL_ENGINE_RESONANCE", "").strip() == "1"
        env_autostart = os.getenv("GLYPH_GOAL_ENGINE_AUTOSTART", "").strip() == "1"
        env_broadcast = os.getenv("GLYPH_GOAL_ENGINE_BROADCAST", "").strip() == "1"

        self.resonance_enabled = env_res if resonance_enabled is None else bool(resonance_enabled)
        self.broadcast_enabled = env_broadcast if broadcast_enabled is None else bool(broadcast_enabled)
        self._autostart_resonance = env_autostart if autostart_resonance is None else bool(autostart_resonance)

        # resonance runtime objects (created only if enabled)
        self.rmc: Optional[ResonantMemoryCache] = None
        self.heartbeat: Optional[ResonanceHeartbeat] = None
        self._heartbeat_started = False

        # throttles (avoid disk spam / log spam)
        self._last_rmc_save_ts = 0.0
        self._last_goal_save_ts = 0.0
        self._last_broadcast_ts = 0.0

        if self.resonance_enabled:
            try:
                self.rmc = ResonantMemoryCache()
                self.heartbeat = ResonanceHeartbeat(namespace="goal_engine")
                self.heartbeat.register_listener(self._on_heartbeat)

                if self._autostart_resonance:
                    self.start_resonance()
                else:
                    log.info("🧠 GoalEngine resonance enabled (heartbeat NOT started; set GLYPH_GOAL_ENGINE_AUTOSTART=1 to autostart).")
            except Exception as e:
                # Never crash app on init
                self.rmc = None
                self.heartbeat = None
                self._heartbeat_started = False
                log.warning(f"⚠️ GoalEngine resonance init failed (disabled): {e}")

    # ---------------------------------------------------------
    # Lifecycle controls (IMPORTANT: no autostart by default)
    # ---------------------------------------------------------
    def start_resonance(self) -> None:
        if not self.resonance_enabled:
            log.info("GoalEngine.start_resonance: resonance is disabled.")
            return
        if self.heartbeat is None:
            log.warning("GoalEngine.start_resonance: heartbeat is not initialized.")
            return
        if self._heartbeat_started:
            return
        try:
            self.heartbeat.start()
            self._heartbeat_started = True
            log.info("💓 GoalEngine heartbeat started.")
        except Exception as e:
            log.warning(f"⚠️ Failed to start GoalEngine heartbeat: {e}")

    def stop_resonance(self) -> None:
        hb = self.heartbeat
        if hb is None or not self._heartbeat_started:
            return
        try:
            # ResonanceHeartbeat may or may not expose stop(); be defensive.
            stop_fn = getattr(hb, "stop", None)
            if callable(stop_fn):
                stop_fn()
            self._heartbeat_started = False
            log.info("🛑 GoalEngine heartbeat stopped.")
        except Exception as e:
            log.warning(f"⚠️ Failed to stop GoalEngine heartbeat: {e}")

    # ---------------------------------------------------------
    def get_all_goals(self):
        return self.goals

    def register_agent(self, agent):
        if agent not in self.agents:
            self.agents.append(agent)
            log.info(f"✅ Agent registered: {getattr(agent, 'name', 'unknown')}")

    # ---------------------------------------------------------
    # 🔄 Persistence
    # ---------------------------------------------------------
    def load_goals(self):
        try:
            if self.goal_file.exists():
                with self.goal_file.open("r") as f:
                    data = json.load(f)
                self.goals = data.get("goals", []) or []
                self.completed = data.get("completed", []) or []
                log.info(f"📂 Loaded {len(self.goals)} goals from {self.goal_file}")
            else:
                # Do NOT auto-create or save on missing file (prevents spam on fresh boots)
                self.goals, self.completed = [], []
                log.info(f"ℹ️ No goal file at {self.goal_file} (starting empty).")
        except Exception as e:
            log.warning(f"⚠️ Goal file load error: {e}")
            self.goals, self.completed = [], []

    def save_goals(self, *, force: bool = False):
        """
        Save goals to disk.

        Default behavior:
          - If goals empty and force=False: skip (prevents constant overwrite/log spam)
        """
        try:
            if not force and not self.goals:
                return
            self.goal_file.parent.mkdir(parents=True, exist_ok=True)
            with self.goal_file.open("w") as f:
                json.dump({"goals": self.goals, "completed": self.completed}, f, indent=2)
        except Exception as e:
            log.warning(f"⚠️ Failed to save goals: {e}")

    def load_log(self):
        try:
            if self.log_file.exists():
                with self.log_file.open("r") as f:
                    self.log = json.load(f)
            else:
                self.log = []
        except Exception:
            self.log = []

    def save_log(self):
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("w") as f:
                json.dump(self.log, f, indent=2)
        except Exception as e:
            log.warning(f"⚠️ Failed to save goal log: {e}")

    # ---------------------------------------------------------
    # 🧠 Goal state
    # ---------------------------------------------------------
    def get_active_goals(self):
        completed_set = set(self.completed)
        actives = [
            g
            for g in self.goals
            if g.get("name") not in completed_set
            and all(dep in completed_set for dep in g.get("dependencies", []))
        ]
        actives.sort(key=lambda g: g.get("priority", 0), reverse=True)
        return actives

    def mark_complete(self, goal_name, **meta):
        for g in self.goals:
            if g.get("name") == goal_name and goal_name not in self.completed:
                g["completed_at"] = _utc_now_iso()
                self.completed.append(goal_name)
                self.save_goals(force=True)

                entry = {"goal": goal_name, **meta, "timestamp": _utc_now_iso()}
                self.log.append(entry)
                self.save_log()

                log.info(f"✅ Goal complete -> {goal_name}")
                return g
        log.warning(f"⚠️ Goal not found or already complete: {goal_name}")
        return None

    # ---------------------------------------------------------
    # 🎯 Goal creation
    # ---------------------------------------------------------
    def assign_goal(self, goal: Dict[str, Any]):
        if not self.enable_glyph_logging:
            log.warning("🚫 Glyph logging disabled.")
            return goal

        name = goal.get("name")
        if not name:
            log.warning("⚠️ assign_goal: missing goal['name']")
            return None

        names = [g.get("name") for g in self.goals]
        if name in names:
            log.warning(f"⚠️ Duplicate goal: {name}")
            return None

        # Inject to KG (best effort)
        try:
            get_goal_engine_kg_writer().inject_glyph(
                content=goal.get("description", ""),
                glyph_type="goal",
                metadata={
                    **{
                        k: goal.get(k)
                        for k in ("name", "reward", "priority", "origin_strategy_id", "origin_glyph", "origin")
                    },
                    "tags": (goal.get("tags") or []) + ["🎯"],
                    "created_at": goal.get("created_at") or _utc_now_iso(),
                },
                plugin="GoalEngine",
            )
        except Exception as e:
            log.warning(f"⚠️ KG injection failed: {e}")

        self.goals.append(goal)
        self.save_goals(force=True)
        log.info(f"✅ Goal assigned: {name}")

        # Trigger Tessaris logic (best effort)
        try:
            trigger_tessaris_from_goal(goal)
        except Exception as e:
            log.warning(f"⚠️ Tessaris trigger failed: {e}")

        # Glyph synthesis (best effort; keep it isolated)
        try:
            import requests  # local import to reduce module-load side effects

            r = requests.post(
                f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
                json={"text": goal.get("description", ""), "source": "goal"},
                timeout=10,
            )
            if r.status_code == 200:
                count = len(r.json().get("glyphs", []))
                log.info(f"✨ Synthesized {count} glyphs from goal.")
        except Exception as e:
            log.debug(f"Glyph synthesis skipped/failed: {e}")

        return goal

    # ---------------------------------------------------------
    # ⚛ Resonance Feedback Loop
    # ---------------------------------------------------------
    def _on_heartbeat(self, pulse: dict):
        """
        Listener invoked by ResonanceHeartbeat.

        IMPORTANT:
          - Must be cheap.
          - Must not spin event loops.
          - Must not spam disk writes.
        """
        if not self.resonance_enabled:
            return

        try:
            coherence = float(pulse.get("Φ_coherence", 0.5))
            entropy = float(pulse.get("Φ_entropy", 0.5))
            sqi = float(pulse.get("sqi", 0.5))
            delta = abs(coherence - entropy)

            # --- RMC update (throttled saves)
            if self.rmc is not None:
                self.rmc.push_sample(rho=coherence, entropy=entropy, sqi=sqi, delta=delta)

                now = time.time()
                if now - self._last_rmc_save_ts >= 10.0:  # throttle
                    self._last_rmc_save_ts = now
                    try:
                        self.rmc.save()
                    except Exception as e:
                        log.debug(f"RMC save skipped/failed: {e}")

            # --- Entropy-based goal decay (cheap) + throttled persistence
            if self.goals:
                for g in self.goals:
                    pr = float(g.get("priority", 1.0))
                    g["priority"] = max(0.1, round(pr * (1.0 - (entropy * 0.02)), 3))

                now = time.time()
                if now - self._last_goal_save_ts >= 15.0:  # throttle
                    self._last_goal_save_ts = now
                    self.save_goals(force=True)

            # --- Optional broadcast (OFF by default; throttle hard)
            if self.broadcast_enabled:
                now = time.time()
                if now - self._last_broadcast_ts >= 2.0:
                    self._last_broadcast_ts = now
                    ws_payload = {
                        "event": "goal_resonance_update",
                        "data": {"entropy": entropy, "sqi": sqi, "goal_count": len(self.goals)},
                    }

                    # If we're already inside a running loop, schedule it.
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._broadcast_ws(ws_payload))
                    except RuntimeError:
                        # No running loop here; best-effort: skip (don’t create new loops/threads).
                        pass

        except Exception as e:
            log.warning(f"[goal_engine::Heartbeat] listener error: {e}")

    async def _broadcast_ws(self, payload: dict) -> None:
        try:
            from backend.modules.websocket_manager import WebSocketManager

            await WebSocketManager().broadcast(message=payload)
        except Exception as e:
            log.debug(f"GoalEngine ws broadcast skipped/failed: {e}")


# ✅ Singleton (SAFE: no heartbeat autostart unless env says so)
GOALS = GoalEngine()

if __name__ == "__main__":
    # If you explicitly want heartbeat in CLI runs:
    #   GLYPH_GOAL_ENGINE_RESONANCE=1 GLYPH_GOAL_ENGINE_AUTOSTART=1 python goal_engine.py
    print("🎯 Active Goals:")
    for g in GOALS.get_active_goals():
        print(f"- {g.get('name')} (priority={g.get('priority')}, reward={g.get('reward')})")