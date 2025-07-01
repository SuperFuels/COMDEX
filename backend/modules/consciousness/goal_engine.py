from datetime import datetime
from modules.hexcore.memory_engine import MemoryEngine

class GoalEngine:
    def __init__(self):
        self.goals = []
        self.memory = MemoryEngine()

    def add_goal(self, goal, priority="medium", source="internal"):
        goal_obj = {
            "goal": goal,
            "priority": priority,
            "status": "active",
            "source": source,
            "created_at": datetime.utcnow().isoformat()
        }
        self.goals.append(goal_obj)
        self.memory.store({
            "label": f"goal_{priority}",
            "content": f"Goal created: {goal}"
        })
        print(f"[GOAL ENGINE] Added goal: {goal}")

    def list_goals(self, status_filter="active"):
        return [g for g in self.goals if g["status"] == status_filter]

    def mark_complete(self, goal_text):
        for g in self.goals:
            if g["goal"] == goal_text:
                g["status"] = "complete"
                self.memory.store({
                    "label": "goal_completed",
                    "content": f"Goal completed: {goal_text}"
                })
                print(f"[GOAL ENGINE] Completed goal: {goal_text}")
                return True
        print(f"[GOAL ENGINE] Goal not found: {goal_text}")
        return False

    def run_daily_goals(self):
        self.add_goal("Reflect on recent dreams", priority="high")
        self.add_goal("Analyze memory patterns", priority="medium")
        self.add_goal("Generate plan to increase compute power", priority="high")

    def get_status_report(self):
        active = len(self.list_goals("active"))
        completed = len(self.list_goals("complete"))
        return {
            "active_goals": active,
            "completed_goals": completed,
            "total_goals": active + completed
        }
