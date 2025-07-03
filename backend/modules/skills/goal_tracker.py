# backend/modules/skills/goal_tracker.py

from typing import List, Dict
import json
import os

GOAL_FILE = "backend/modules/skills/goals.json"  # full relative path

class GoalTracker:
    def __init__(self):
        self.goals: List[Dict] = []
        self.load_goals()

    def load_goals(self):
        if os.path.exists(GOAL_FILE):
            with open(GOAL_FILE, "r") as f:
                data = json.load(f)
                self.goals = data.get("goals", [])
        else:
            self.goals = []

    def save_goals(self):
        with open(GOAL_FILE, "w") as f:
            json.dump({"goals": self.goals}, f, indent=2)

    def add_goal(self, name: str, status: str = "pending"):
        goal = {
            "name": name,
            "status": status
        }
        self.goals.append(goal)
        self.save_goals()
        return goal

    def update_goal(self, index: int, status: str):
        if 0 <= index < len(self.goals):
            self.goals[index]["status"] = status
            self.save_goals()
            return self.goals[index]
        return None

    def get_goals(self, status_filter: str = None):
        if status_filter:
            return [g for g in self.goals if g.get("status") == status_filter]
        return self.goals