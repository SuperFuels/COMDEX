"""
GoalEngine - Phase 36B : Autonomous Goal Formation
--------------------------------------------------
Implements self-generated goal objects within the Aion substrate.
Goals emerge from RSI drift, entropy balance, and PAL reflection metrics.

Each goal has:
  * intent        - textual description ("seek equilibrium")
  * priority      - derived from RSI variance / entropy imbalance
  * satisfaction  - dynamic reinforcement level (0 - 1)
  * lineage       - links to concept(s) and emotional state vectors
"""

import time
import json
import math
import logging
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

GOAL_LOG = Path("data/analysis/goal_events.jsonl")
GOAL_STATE = Path("data/state/active_goals.json")

# ─────────────────────────────────────────────
@dataclass
class Goal:
    id: str
    intent: str
    priority: float
    satisfaction: float
    origin: str
    timestamp: float = 0.0

    def __post_init__(self):
        # auto-assign timestamp if missing
        if not self.timestamp:
            self.timestamp = time.time()

# ─────────────────────────────────────────────
class GoalEngine:
    """
    Phase 36B - Autonomous Goal Formation Engine
    --------------------------------------------
    Handles creation, persistence, and reinforcement of introspective goals.
    Goals emerge from RSI variance, entropy fluctuations, and self-accuracy drift.
    """

    def __init__(self):
        self.active_goals: dict[str, Goal] = {}
        self._load_state()

    # ─────────────────────────────────────────────
    def create(self, goal_name, priority=0.5, source="system", metadata=None):
        """
        Register a new goal into the active goal pool.
        This allows InstructionInterpreter and other modules
        to spawn intent nodes that Aion can act upon or track.
        """
        if not goal_name:
            return None

        goal = {
            "name": goal_name,
            "priority": priority,
            "source": source,
            "timestamp": time.time(),
            "metadata": metadata or {},
            "status": "active"
        }

        # Store or append to the goal registry
        if not hasattr(self, "goals"):
            self.goals = []

        self.goals.append(goal)

        print(f"[GoalEngine] 🎯 Created goal: {goal_name} (priority={priority}, source={source})")
        return goal

    # ─────────────────────────────────────────
    def _load_state(self):
        if GOAL_STATE.exists():
            try:
                data = json.load(open(GOAL_STATE))
                for g in data.get("goals", []):
                    self.active_goals[g["id"]] = Goal(**g)
                logger.info(f"[GoalEngine] Loaded {len(self.active_goals)} active goals from state")
            except Exception as e:
                logger.warning(f"[GoalEngine] Could not load state: {e}")

    def _save_state(self):
        GOAL_STATE.parent.mkdir(parents=True, exist_ok=True)
        with open(GOAL_STATE, "w") as f:
            json.dump(
                {
                    "timestamp": time.time(),
                    "goals": [asdict(g) for g in self.active_goals.values()],
                },
                f,
                indent=2,
            )

    # ─────────────────────────────────────────
    def create_goal(self, intent: str | None = None, priority: float = 0.0, origin="introspective", **kwargs) -> Goal:
        """
        Create and register a new goal.

        Args:
            intent or name: Textual goal description.
            priority: Importance (0.0 - 1.0).
            origin: Source system or process spawning it.
        """
        # Back-compat: allow 'name' arg
        if intent is None:
            intent = kwargs.get("name", "unnamed_goal")

        gid = f"goal:{intent.replace(' ', '_')}"
        g = Goal(
            id=gid,
            intent=intent,
            priority=float(max(0.0, min(1.0, priority))),
            satisfaction=0.0,
            origin=origin,
        )
        self.active_goals[gid] = g
        self._log_event(g, "created")
        self._save_state()
        logger.info(f"[GoalEngine] Created goal '{intent}' (priority={priority:.2f})")
        return g

    # ─────────────────────────────────────────
    def update_satisfaction(self, gid: str, delta: float):
        """Reinforce or decay satisfaction value for an existing goal."""
        g = self.active_goals.get(gid)
        if not g:
            return
        g.satisfaction = max(0.0, min(1.0, g.satisfaction + delta))
        self._log_event(g, "reinforced" if delta > 0 else "decayed")
        self._save_state()

    # ─────────────────────────────────────────
    def evaluate_goals(self, rsi_var: float, entropy: float):
        """
        Periodically called by introspective_goal_bridge.
        - High entropy -> spawn 'seek equilibrium'
        - RSI variance ↑ -> spawn 'reduce drift'
        - Stability plateau -> reinforce 'preserve Φ'
        """
        if entropy > 0.7:
            self.create_goal("seek equilibrium", priority=entropy)
        if rsi_var > 0.6:
            self.create_goal("reduce drift", priority=rsi_var)
        if entropy < 0.3 and rsi_var < 0.3:
            self.create_goal("preserve Φ", priority=1.0 - entropy)

    # ─────────────────────────────────────────
    def decay_inactive_goals(self, decay_rate: float = 0.02):
        """Slowly decay satisfaction over time (Phase 36C pre-hook)."""
        now = time.time()
        for gid, g in list(self.active_goals.items()):
            age = now - g.timestamp
            if age > 60:
                g.satisfaction = max(0.0, g.satisfaction - decay_rate)
        self._save_state()

    # ─────────────────────────────────────────
    def _log_event(self, goal: Goal, event: str):
        GOAL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(GOAL_LOG, "a") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": time.time(),
                        "goal_id": goal.id,
                        "intent": goal.intent,
                        "priority": goal.priority,
                        "satisfaction": goal.satisfaction,
                        "origin": goal.origin,
                        "event": event,
                    }
                )
                + "\n"
            )

# ─────────────────────────────────────────────
# Phase 36B - Global GoalEngine Instance
# Tessaris / Aion Research Division
# ─────────────────────────────────────────────
try:
    GOALS  # if already defined elsewhere, skip
except NameError:
    try:
        GOALS = GoalEngine()
        print("🧭 GoalEngine global instance initialized as GOALS")
    except Exception as e:
        print(f"⚠️ Could not initialize global GOALS instance: {e}")
        GOALS = None