import json
from datetime import datetime
from pathlib import Path

GOAL_FILE = Path(__file__).parent / "goals.json"

class GoalEngine:
    def __init__(self):
        self.goals = []
        self.completed = []
        self.load_goals()

    def load_goals(self):
        if GOAL_FILE.exists():
            with open(GOAL_FILE, "r") as f:
                data = json.load(f)
                self.goals = data.get("goals", [])
                self.completed = data.get("completed", [])
        else:
            self.save_goals()

    def save_goals(self):
        with open(GOAL_FILE, "w") as f:
            json.dump({"goals": self.goals, "completed": self.completed}, f, indent=2)

    def get_active_goals(self):
        return [g for g in self.goals if g.get("name") not in self.completed]

    def mark_complete(self, goal_name):
        for goal in self.goals:
            if goal["name"] == goal_name and goal_name not in self.completed:
                self.completed.append(goal_name)
                goal["completed_at"] = datetime.now().isoformat()
                self.save_goals()
                return goal
        return None

    def assign_goal(self, goal):
        self.goals.append(goal)
        self.save_goals()
        return goal

if __name__ == "__main__":
    engine = GoalEngine()
    print("🎯 Active Goals:")
    for g in engine.get_active_goals():
        print(f"- {g['name']} (reward: {g['reward']})")
