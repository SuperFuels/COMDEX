import random
from datetime import datetime

class PlanningEngine:
    def __init__(self):
        self.active_plan = []
        self.last_generated = None

    def generate_plan(self, goal: str):
        print(f"[PLANNING] Generating plan for: {goal}")
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

        self.active_plan = plan_templates.get(goal, ["No plan available for that goal"])
        self.last_generated = datetime.now()
        return self.active_plan

    def get_current_plan(self):
        return self.active_plan

    def step_through_plan(self):
        if not self.active_plan:
            print("[PLANNING] No plan available.")
            return None
        next_step = self.active_plan.pop(0)
        print(f"[PLANNING] Executing step: {next_step}")
        return next_step
