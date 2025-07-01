from typing import List, Dict
import json
import os

GOAL_FILE = "aion_goals.json"

class GoalTracker:
    def __init__(self):
        self.goals: List[Dict] = []
        self.load_goals()

    def load_goals(self):
        if os.path.exists(GOAL_FILE):
            with open(GOAL_FILE, "r") as f:
                self.goals = json.load(f)
        else:
            self.goals = []

    def save_goals(self):
        with open(GOAL_FILE, "w") as f:
            json.dump(self.goals, f, indent=2)

    def add_goal(self, title: str, status: str = "pending"):
        goal = {
            "title": title,
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
            return [g for g in self.goals if g["status"] == status_filter]
        return self.goals
