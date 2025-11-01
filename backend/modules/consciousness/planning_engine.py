#!/usr/bin/env python3
"""
🧭 PlanningEngine - Phase 54 Resonant Context Coupling
───────────────────────────────────────────────────────────────
Integrates Θ-field resonance and ContextEngine environmental entropy
to dynamically modulate planning "temperature" - i.e., the stochastic
variance in strategic path selection.

Features:
  * Context ↔ Planning entropy bridge
  * Θ-field resonance feedback (SQI, ΔΦ)
  * Plan temperature modulation based on context entropy
  * Memory logging + harmonic emission
"""

import random
import math
import time
from datetime import datetime
from pathlib import Path

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ✅ Core Modules
from backend.modules.hexcore.memory_engine import MemoryEngine

# ⚛ Resonance Integrations
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

# 🌍 Context Coupling
try:
    from backend.modules.consciousness.context_engine import ContextEngine
except Exception:
    ContextEngine = None


class PlanningEngine:
    def __init__(self):
        self.active_plan = []
        self.current_goal = None
        self.last_generated = None
        self.temperature = 1.0  # dynamic "reasoning temperature"

        # 🧠 Submodules
        from backend.modules.skills.goal_engine import GoalEngine
        from backend.modules.skills.strategy_planner import StrategyPlanner

        self.goal_engine = GoalEngine()
        self.memory = MemoryEngine()
        self.strategist = StrategyPlanner()

        # ⚛ Resonant Components
        self.Θ = ResonanceHeartbeat(namespace="planning", base_interval=1.8)
        self.RMC = ResonantMemoryCache()
        self.resonance_log = Path("data/analysis/planning_resonance_feed.jsonl")
        self.resonance_log.parent.mkdir(parents=True, exist_ok=True)

        # 🌍 Context Coupling
        self.context = ContextEngine() if ContextEngine else None
        self.last_entropy = 0.0

    # ------------------------------------------------------------
    def _compute_environment_entropy(self) -> float:
        """Compute entropy score from ContextEngine (0-1)."""
        if not self.context:
            return 0.5  # neutral baseline
        ctx = self.context.get_context()
        env = ctx.get("environment", "default").lower()

        # heuristic: known env noise levels
        entropy_map = {
            "default": 0.5,
            "stable": 0.3,
            "dynamic": 0.6,
            "chaotic": 0.8,
            "crisis": 0.9,
            "learning": 0.7,
        }
        entropy = entropy_map.get(env, 0.5)
        self.last_entropy = entropy
        return entropy

    # ------------------------------------------------------------
    def _update_temperature(self):
        """Update internal planning temperature based on entropy."""
        entropy = self._compute_environment_entropy()
        base_T = 1.0
        kE = 0.75
        self.temperature = round(base_T * (1 + kE * (entropy - 0.5)), 3)
        return self.temperature

    # ------------------------------------------------------------
    def generate_plan(self, goal_name: str):
        print(f"[PLANNING] Generating plan for: {goal_name}")
        self.current_goal = goal_name
        self._update_temperature()

        plan_templates = {
            "increase_energy": [
                "Analyze compute usage",
                "Identify idle cycles",
                "Schedule energy-saving mode",
                "Request cloud credits",
                "Run low-power dream mode"
            ],
            "earn_money": [
                "Scan crypto market for opportunities",
                "Analyze token trends",
                "Propose value-generating task",
                "Execute & monitor result",
                "Reinvest surplus into compute credits"
            ],
            "unlock_skill": [
                "Review memory and knowledge gaps",
                "Request skill module from Kevin",
                "Load module via boot_loader",
                "Reflect on results",
                "Store learnings"
            ],
            "self_optimize": [
                "Review performance logs",
                "Identify bottlenecks",
                "Simulate new routines",
                "Implement improvements",
                "Validate outcomes"
            ]
        }

        plan = plan_templates.get(goal_name, [
            "Understand goal context",
            "Break down goal into subtasks",
            "Schedule subtasks in order",
            "Execute each and reflect on outcome"
        ])

        # 🎲 Shuffle with entropy-weighted temperature
        randomness = min(1.0, max(0.0, self.temperature - 0.8))
        if randomness > 0:
            random.shuffle(plan)
            if randomness > 0.3:
                # optional insertion of creative step
                plan.insert(
                    random.randint(0, len(plan) - 1),
                    "Run harmonic reflection before execution"
                )

        self.active_plan = plan
        self.last_generated = datetime.now()

        # ⚛ Emit resonance pulse for plan synthesis
        pulse = self.Θ.tick()
        rho = pulse.get("Φ_coherence", 0.7)
        I = pulse.get("Φ_entropy", self.last_entropy)
        sqi = round((rho + (1 - abs(0.5 - I))) / 2, 3)
        delta_phi = round(abs(rho - I), 3)

        self.RMC.push_sample(rho=rho, entropy=I, sqi=sqi, delta=delta_phi)
        self.RMC.save()

        # Log plan event
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "goal": goal_name,
            "env_entropy": I,
            "temperature": self.temperature,
            "ρ": rho,
            "Ī": I,
            "SQI": sqi,
            "ΔΦ": delta_phi,
            "steps": len(plan)
        }
        with open(self.resonance_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"[Θ🧭] Planning resonance -> SQI={sqi:.3f}, ΔΦ={delta_phi:.3f}, T={self.temperature:.2f}")
        return self.active_plan

    # ------------------------------------------------------------
    def get_current_plan(self):
        return self.active_plan

    def step_through_plan(self):
        """Execute next step of the plan with context-modulated variation."""
        if not self.active_plan:
            print("[PLANNING] No active plan available.")
            return None

        step = self.active_plan.pop(0)
        entropy = self._compute_environment_entropy()
        jitter = random.uniform(-0.1, 0.1) * self.temperature
        adjusted_entropy = max(0, min(1, entropy + jitter))

        timestamp = datetime.now().isoformat()
        print(f"[PLANNING] Executing step (T={self.temperature:.2f}, E={adjusted_entropy:.2f}): {step}")

        self.memory.store("plan_step", {
            "type": "planning_step",
            "goal": self.current_goal or "unspecified",
            "step": step,
            "entropy": adjusted_entropy,
            "temperature": self.temperature,
            "timestamp": timestamp
        })

        return step

    # ------------------------------------------------------------
    def strategize(self):
        """High-level strategy loop with automatic goal recall."""
        if not self.active_plan:
            print("[PLANNING] No active plan. Pulling top goal.")
            top_goals = self.goal_engine.get_active_goals()
            if not top_goals:
                print("[PLANNING] No active goals found. Generating default strategy.")
                default_goal = self.strategist.generate_goal()
                self.generate_plan(default_goal)
            else:
                goal_name = top_goals[0].get("name", "self_optimize")
                self.generate_plan(goal_name)

        step = self.step_through_plan()
        if step:
            print(f"[PLANNING] Strategy step executed: {step}")
        else:
            print("[PLANNING] Plan completed or empty.")


# ✅ Safe, lazy-import module-level access function
_planner_instance = None
def enqueue_plan(goal_name: str):
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = PlanningEngine()
    return _planner_instance.generate_plan(goal_name)