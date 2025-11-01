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
"""

import json, requests, asyncio, logging
from datetime import datetime
from pathlib import Path
from backend.config import GLYPH_API_BASE_URL, ENABLE_GLYPH_LOGGING
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

DNA_SWITCH.register(__file__)

log = logging.getLogger(__name__)

# Delayed imports to avoid circular dependencies
def trigger_tessaris_from_goal(*a, **kw):
    from backend.modules.tessaris.tessaris_trigger import trigger_tessaris_from_goal as _t
    return _t(*a, **kw)

from backend.modules.glyphos.glyph_mutator import run_self_rewrite
from backend.modules.glyphos.entanglement_utils import entangle_glyphs
from backend.modules.glyphnet.glyphnet_trace import log_trace_event


# 🔗 Knowledge Graph writer singleton
kg_writer = None
def get_goal_engine_kg_writer():
    global kg_writer
    if kg_writer is None:
        from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
        kg_writer = get_kg_writer()
    return kg_writer


# ============================================================
# ⚙️ Persistent Paths (Unified)
# ============================================================
GOAL_FILE = Path("/workspaces/COMDEX/data/goals/goal_engine_data.json")
LOG_FILE = Path("/workspaces/COMDEX/data/goals/goal_skill_log.json")
GOAL_FILE.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# ⚙️ Core Goal Engine
# ============================================================
class GoalEngine:
    def __init__(self, enable_glyph_logging=ENABLE_GLYPH_LOGGING, goal_file=None):
        # Configurable goal file location
        self.enable_glyph_logging = enable_glyph_logging
        self.goal_file = Path(goal_file or "/workspaces/COMDEX/data/goals/goal_engine_data.json")
        self.log_file = self.goal_file.parent / "goal_skill_log.json"

        # Ensure directory exists before any load/save
        self.goal_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize internal state
        self.goals, self.completed, self.log = [], [], []
        self.agents = []

        # Load persisted data
        self.load_goals()
        self.load_log()

        # 🔮 Resonant subsystems
        self.rmc = ResonantMemoryCache()
        self.heartbeat = ResonanceHeartbeat(namespace="goal_engine")
        self.heartbeat.register_listener(self._on_heartbeat)
        self.heartbeat.start()
        log.info("💓 GoalEngine linked to Resonance Heartbeat + RMC.")

    # ---------------------------------------------------------
    def get_all_goals(self):
        return self.goals

    def register_agent(self, agent):
        if agent not in self.agents:
            self.agents.append(agent)
            log.info(f"✅ Agent registered: {getattr(agent, 'name', 'unknown')}")

    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # 🔄 Persistence
    def load_goals(self):
        try:
            if self.goal_file.exists():
                with open(self.goal_file, "r") as f:
                    data = json.load(f)
                self.goals = data.get("goals", [])
                self.completed = data.get("completed", [])
                log.info(f"📂 Loaded {len(self.goals)} goals from {self.goal_file}")
            else:
                log.warning(f"⚠️ No existing goal file at {self.goal_file}, initializing new one.")
                self.save_goals()
        except Exception as e:
            log.warning(f"⚠️ Goal file load error: {e}")
            self.goals, self.completed = [], []

    def save_goals(self):
        try:
            if not self.goals:
                log.warning(f"⚠️ Attempting to save empty goal list to {self.goal_file} - skipping overwrite.")
                return
            self.goal_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.goal_file, "w") as f:
                json.dump({"goals": self.goals, "completed": self.completed}, f, indent=2)
            log.info(f"💾 Saved {len(self.goals)} goals -> {self.goal_file}")
        except Exception as e:
            log.warning(f"⚠️ Failed to save goals: {e}")

    def load_log(self):
        try:
            if LOG_FILE.exists():
                with LOG_FILE.open("r") as f:
                    self.log = json.load(f)
            else:
                self.save_log()
        except Exception:
            self.log = []

    def save_log(self):
        try:
            with LOG_FILE.open("w") as f:
                json.dump(self.log, f, indent=2)
        except Exception as e:
            log.warning(f"⚠️ Failed to save goal log: {e}")

    # ---------------------------------------------------------
    # 🧠 Goal state
    def get_active_goals(self):
        completed_set = set(self.completed)
        actives = [
            g for g in self.goals
            if g["name"] not in completed_set
            and all(dep in completed_set for dep in g.get("dependencies", []))
        ]
        actives.sort(key=lambda g: g.get("priority", 0), reverse=True)
        return actives

    def mark_complete(self, goal_name, **meta):
        for g in self.goals:
            if g.get("name") == goal_name and goal_name not in self.completed:
                g["completed_at"] = datetime.now().isoformat()
                self.completed.append(goal_name)
                self.save_goals()
                entry = {"goal": goal_name, **meta, "timestamp": datetime.now().isoformat()}
                self.log.append(entry)
                self.save_log()
                log.info(f"✅ Goal complete -> {goal_name}")
                return g
        log.warning(f"⚠️ Goal not found or already complete: {goal_name}")

    # ---------------------------------------------------------
    # 🎯 Goal creation
    def assign_goal(self, goal):
        if not self.enable_glyph_logging:
            log.warning("🚫 Glyph logging disabled.")
            return goal

        names = [g.get("name") for g in self.goals]
        if goal["name"] in names:
            log.warning(f"⚠️ Duplicate goal: {goal['name']}")
            return None

        # Inject to KG
        try:
            get_goal_engine_kg_writer().inject_glyph(
                content=goal["description"],
                glyph_type="goal",
                metadata={
                    **{k: goal.get(k) for k in
                       ("name", "reward", "priority", "origin_strategy_id", "origin_glyph", "origin")},
                    "tags": goal.get("tags", []) + ["🎯"],
                    "created_at": goal["created_at"]
                },
                plugin="GoalEngine"
            )
        except Exception as e:
            log.warning(f"⚠️ KG injection failed: {e}")

        self.goals.append(goal)
        self.save_goals()
        log.info(f"✅ Goal assigned: {goal['name']}")

        # Trigger Tessaris logic
        try:
            trigger_tessaris_from_goal(goal)
        except Exception as e:
            log.warning(f"⚠️ Tessaris trigger failed: {e}")

        # Glyph synthesis
        try:
            r = requests.post(
                f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
                json={"text": goal["description"], "source": "goal"},
                timeout=10,
            )
            if r.status_code == 200:
                count = len(r.json().get("glyphs", []))
                log.info(f"✨ Synthesized {count} glyphs from goal.")
        except Exception as e:
            log.error(f"🚨 Glyph synthesis error: {e}")

        return goal

    # ---------------------------------------------------------
    # ⚛ Resonance Feedback Loop
    def _on_heartbeat(self, pulse: dict):
        try:
            coherence = pulse.get("Φ_coherence", 0.5)
            entropy = pulse.get("Φ_entropy", 0.5)
            sqi = pulse.get("sqi", 0.5)
            delta = abs(coherence - entropy)

            self.rmc.push_sample(rho=coherence, entropy=entropy, sqi=sqi, delta=delta)
            self.rmc.save()

            # Entropy-based goal decay
            for g in self.goals:
                pr = g.get("priority", 1.0)
                g["priority"] = max(0.1, round(pr * (1.0 - (entropy * 0.02)), 3))
            self.save_goals()

            # Broadcast async
            from backend.modules.websocket_manager import WebSocketManager
            ws_payload = {
                "event": "goal_resonance_update",
                "data": {"entropy": entropy, "sqi": sqi, "goal_count": len(self.goals)},
            }
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(WebSocketManager().broadcast(message=ws_payload))

        except Exception as e:
            log.warning(f"[goal_engine::Heartbeat] listener error: {e}")


# ✅ Singleton
GOALS = GoalEngine()

if __name__ == "__main__":
    print("🎯 Active Goals:")
    for g in GOALS.get_active_goals():
        print(f"- {g['name']} (priority={g.get('priority')}, reward={g.get('reward')})")