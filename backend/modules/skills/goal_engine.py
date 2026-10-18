# backend/modules/skills/goal_engine.py
"""
Goal engine (skills/goal_engine).

IMPORTANT (sanity):
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
# ⚙️ Persistent Paths (LOCAL SAFE) — NO /workspaces
# ============================================================
def _repo_root() -> Path:
    # goal_engine.py -> backend/modules/skills/goal_engine.py
    return Path(__file__).resolve().parents[3]


DATA_ROOT = Path(os.getenv("TESSARIS_DATA_ROOT", str(_repo_root() / "data"))).resolve()
GOALS_DIR = DATA_ROOT / "goals"
DEFAULT_GOAL_FILE = GOALS_DIR / "goals.json"

# Keep log next to the goal file by default
DEFAULT_LOG_FILE = GOALS_DIR / "goal_skill_log.json"

GOALS_DIR.mkdir(parents=True, exist_ok=True)


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

        # ---------------------------------------------------------
        # 🆕 FIELD / REWARD STATE (ADDITIVE ONLY; NON-BREAKING)
        # ---------------------------------------------------------
        self._last_field_state: Optional[Dict[str, Any]] = None
        self._last_field_reward: float = 0.0
        self._last_goal_suggestions: List[str] = []
        self._last_reinforcement_event: Optional[Dict[str, Any]] = None

        if self.resonance_enabled:
            try:
                self.rmc = ResonantMemoryCache()
                self.heartbeat = ResonanceHeartbeat(namespace="goal_engine")
                self.heartbeat.register_listener(self._on_heartbeat)

                if self._autostart_resonance:
                    self.start_resonance()
                else:
                    log.info(
                        "🧠 GoalEngine resonance enabled (heartbeat NOT started; set "
                        "GLYPH_GOAL_ENGINE_AUTOSTART=1 to autostart)."
                    )
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
                with self.goal_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                self.goals = data.get("goals", []) or []
                self.completed = data.get("completed", []) or []
                log.info(f"📂 Loaded {len(self.goals)} goals from {self.goal_file}")
            else:
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
            with self.goal_file.open("w", encoding="utf-8") as f:
                json.dump({"goals": self.goals, "completed": self.completed}, f, indent=2)
        except Exception as e:
            log.warning(f"⚠️ Failed to save goals: {e}")

    def load_log(self):
        try:
            if self.log_file.exists():
                with self.log_file.open("r", encoding="utf-8") as f:
                    self.log = json.load(f)
            else:
                self.log = []
        except Exception:
            self.log = []

    def save_log(self):
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("w", encoding="utf-8") as f:
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

    def select_governed_goal(self) -> Optional[Dict[str, Any]]:
        """Select work by explicit authority and verified dependency state."""
        candidates = []
        for goal in self.get_active_goals():
            approval = str(goal.get("approval_policy") or "proposal_only")
            if approval not in {"proposal_only", "autonomous_allowed", "human_approved", "human_approval_required"}:
                continue
            score = float(goal.get("priority") or 0.0)
            score += 1.0 if approval in {"autonomous_allowed", "human_approved"} else 0.0
            score += 0.6 if goal.get("next_outcome_due") or goal.get("deadline") else 0.0
            score += 0.4 if goal.get("blocks_other_goals") else 0.0
            score -= 0.8 if goal.get("status") in {"blocked", "waiting_authority"} else 0.0
            candidates.append((score, goal))
        if not candidates:
            return None
        _, selected = max(candidates, key=lambda row: (row[0], str(row[1].get("name") or "")))
        return {**selected, "selection_authority": "goal_contract_and_verified_dependencies"}

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
    # 🆕 FIELD TELEMETRY → GOALS (ADDITIVE; NON-BREAKING)
    # ---------------------------------------------------------
    def ingest_field_state(self, telemetry: Dict[str, Any], auto_assign: bool = False) -> List[str]:
        """
        Convert field telemetry into goal suggestions.

        This is additive and non-breaking:
          - caches field telemetry
          - suggests goal names
          - only assigns goals if auto_assign=True
        """
        try:
            telemetry = dict(telemetry or {})
            self._last_field_state = telemetry

            coherence = float(telemetry.get("coherence", 0.5))
            delta_phi = float(telemetry.get("delta_phi", 0.0))
            drift = abs(delta_phi)
            entropy = float(telemetry.get("entropy", telemetry.get("psi", 0.5)))
            self_awareness = float(telemetry.get("self_awareness", 0.5))
            global_coherence = float(
                telemetry.get(
                    "global_coherence",
                    telemetry.get("global_coherence_score", coherence),
                )
            )

            suggested_goals: List[str] = []

            # Core field stability triggers
            if drift > 0.20:
                suggested_goals.append("reduce_drift")

            if coherence < 0.50:
                suggested_goals.append("increase_coherence")

            if entropy > 0.75:
                suggested_goals.append("reduce_entropy")

            if self_awareness < 0.25:
                suggested_goals.append("increase_self_awareness")

            if global_coherence < 0.45:
                suggested_goals.append("restore_global_coherence")

            # de-dup while preserving order
            seen = set()
            deduped: List[str] = []
            for g in suggested_goals:
                if g not in seen:
                    deduped.append(g)
                    seen.add(g)

            self._last_goal_suggestions = deduped

            if auto_assign:
                existing_names = {g.get("name") for g in self.goals}
                for goal_name in deduped:
                    if goal_name in existing_names:
                        continue

                    description = {
                        "reduce_drift": "Reduce field drift and stabilize resonance transitions.",
                        "increase_coherence": "Increase field coherence and improve symbolic alignment.",
                        "reduce_entropy": "Lower field entropy and damp unstable symbolic variance.",
                        "increase_self_awareness": "Improve internal awareness coupling and self-alignment.",
                        "restore_global_coherence": "Recover global coherence across symbolic and field layers.",
                    }.get(goal_name, goal_name.replace("_", " ").capitalize())

                    try:
                        self.assign_goal(
                            {
                                "name": goal_name,
                                "description": description,
                                "priority": 1.0,
                                "reward": 1.0,
                                "dependencies": [],
                                "created_at": _utc_now_iso(),
                                "origin": "field_feedback",
                                "tags": ["field", "telemetry", "homeostasis"],
                            }
                        )
                    except Exception as e:
                        log.warning(f"⚠️ Failed to auto-assign field goal '{goal_name}': {e}")

            return deduped

        except Exception as e:
            log.debug(f"[GoalEngine] ingest_field_state failed: {e}")
            return []

    # ---------------------------------------------------------
    # 🆕 FIELD REWARD / REINFORCEMENT (ADDITIVE; NON-BREAKING)
    # ---------------------------------------------------------
    def compute_field_reward(self, telemetry: Dict[str, Any]) -> float:
        """
        Reward heuristic from field telemetry.

        Positive reward:
          - higher coherence
          - higher self awareness
          - lower drift
          - lower entropy

        Returns bounded float in [-1.0, 1.0].
        """
        try:
            telemetry = dict(telemetry or {})
            coherence = float(telemetry.get("coherence", 0.5))
            drift = abs(float(telemetry.get("delta_phi", 0.0)))
            entropy = float(telemetry.get("entropy", telemetry.get("psi", 0.5)))
            self_awareness = float(telemetry.get("self_awareness", 0.5))

            reward = (0.45 * coherence) + (0.25 * self_awareness) - (0.20 * drift) - (0.10 * entropy)
            reward = max(-1.0, min(1.0, round(reward, 4)))
            self._last_field_reward = reward
            return reward
        except Exception as e:
            log.debug(f"[GoalEngine] reward calc failed: {e}")
            self._last_field_reward = 0.0
            return 0.0

    def apply_field_reward(
        self,
        telemetry: Dict[str, Any],
        goal_names: Optional[List[str]] = None,
        *,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """
        Apply a simple reinforcement step to matching goals.

        Non-breaking:
          - only updates priority/reward fields on existing goals
          - does nothing if no matching goals exist
        """
        try:
            reward = self.compute_field_reward(telemetry)
            target_names = list(goal_names or self._last_goal_suggestions or [])
            updated: List[Dict[str, Any]] = []

            if not target_names:
                event = {
                    "timestamp": _utc_now_iso(),
                    "reward": reward,
                    "updated_goals": [],
                    "reason": "no_target_goals",
                    "type": "field_reinforcement",
                }
                self._last_reinforcement_event = event
                return event

            target_name_set = set(target_names)
            for g in self.goals:
                gname = g.get("name")
                if gname not in target_name_set:
                    continue

                current_priority = float(g.get("priority", 1.0))
                current_reward = float(g.get("reward", 1.0))

                # gentle bounded updates to avoid breaking existing behavior
                new_priority = max(0.1, min(10.0, round(current_priority + (reward * 0.25), 3)))
                new_reward = max(0.0, min(10.0, round(current_reward + (reward * 0.25), 3)))

                g["priority"] = new_priority
                g["reward"] = new_reward
                g["last_field_reward"] = reward
                g["last_reinforced_at"] = _utc_now_iso()

                updated.append(
                    {
                        "name": gname,
                        "priority_before": current_priority,
                        "priority_after": new_priority,
                        "reward_before": current_reward,
                        "reward_after": new_reward,
                    }
                )

            if updated and persist:
                self.save_goals(force=True)

            event = {
                "timestamp": _utc_now_iso(),
                "reward": reward,
                "updated_goals": updated,
                "reason": "field_reinforcement",
                "type": "field_reinforcement",
            }
            self._last_reinforcement_event = event
            self.log.append(event)
            self.save_log()
            return event

        except Exception as e:
            log.debug(f"[GoalEngine] apply_field_reward failed: {e}")
            event = {
                "timestamp": _utc_now_iso(),
                "reward": 0.0,
                "updated_goals": [],
                "reason": f"error:{e}",
                "type": "field_reinforcement",
            }
            self._last_reinforcement_event = event
            return event

    # ---------------------------------------------------------
    # 🆕 READ-ONLY ACCESSORS (ADDITIVE; NON-BREAKING)
    # ---------------------------------------------------------
    def get_last_field_state(self) -> Optional[Dict[str, Any]]:
        return self._last_field_state

    def get_last_field_reward(self) -> float:
        return float(self._last_field_reward)

    def get_last_goal_suggestions(self) -> List[str]:
        return list(self._last_goal_suggestions)

    def get_last_reinforcement_event(self) -> Optional[Dict[str, Any]]:
        return self._last_reinforcement_event

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
                if now - self._last_rmc_save_ts >= 10.0:
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
                if now - self._last_goal_save_ts >= 15.0:
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
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._broadcast_ws(ws_payload))
                    except RuntimeError:
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
    print("🎯 Active Goals:")
    for g in GOALS.get_active_goals():
        print(f"- {g.get('name')} (priority={g.get('priority')}, reward={g.get('reward')})")
