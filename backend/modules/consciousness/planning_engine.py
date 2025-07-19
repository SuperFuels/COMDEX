import random
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ✅ Import outside circular deps
from backend.modules.hexcore.memory_engine import MemoryEngine

class PlanningEngine:
    def __init__(self):
        self.active_plan = []
        self.current_goal = None
        self.last_generated = None

        # ✅ Delayed imports to avoid circular dependencies
        from backend.modules.skills.goal_engine import GoalEngine
        from backend.modules.skills.strategy_planner import StrategyPlanner

        self.goal_engine = GoalEngine()
        self.memory = MemoryEngine()
        self.strategist = StrategyPlanner()

    def generate_plan(self, goal_name: str):
        print(f"[PLANNING] Generating plan for: {goal_name}")
        self.current_goal = goal_name

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

        self.active_plan = plan_templates.get(goal_name, [
            "Understand goal context",
            "Break down goal into subtasks",
            "Schedule subtasks in order",
            "Execute each and reflect on outcome"
        ])

        self.last_generated = datetime.now()
        return self.active_plan

    def get_current_plan(self):
        return self.active_plan

    def step_through_plan(self):
        if not self.active_plan:
            print("[PLANNING] No active plan available.")
            return None

        next_step = self.active_plan.pop(0)
        timestamp = datetime.now().isoformat()
        print(f"[PLANNING] Executing step: {next_step}")

        memory_entry = {
            "type": "planning_step",
            "goal": self.current_goal or "unspecified",
            "step": next_step,
            "timestamp": timestamp
        }
        self.memory.store("plan_step", memory_entry)
        return next_step

    def strategize(self):
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