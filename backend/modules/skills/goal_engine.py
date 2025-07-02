import json
from datetime import datetime
from pathlib import Path

GOAL_FILE = Path(__file__).parent / "goals.json"

class GoalEngine:
    def __init__(self):
        self.goals = []
        self.completed = []
        self.agents = []  # For agent communication
        self.load_goals()

    # Agent communication methods
    def register_agent(self, agent):
        if agent not in self.agents:
            self.agents.append(agent)
            print(f"✅ Agent registered: {agent.name}")

    def receive_message(self, message):
        """
        Handle messages from other agents/modules.
        Specifically listens for new milestone notifications to create goals dynamically.
        """
        if isinstance(message, dict):
            msg_type = message.get("type")
            if msg_type == "new_milestone":
                milestone = message.get("milestone", {})
                name = milestone.get("name")
                desc = milestone.get("description", f"Goal related to milestone {name}")
                print(f"📢 Received milestone notification: {name}, creating goal.")
                self.create_goal_from_milestone(name, desc)
            else:
                print(f"📬 Unknown message type received: {msg_type}")
        else:
            print(f"📬 Received message: {message}")

    def load_goals(self):
        if GOAL_FILE.exists():
            try:
                with open(GOAL_FILE, "r") as f:
                    data = json.load(f)
                    self.goals = data.get("goals", [])
                    self.completed = data.get("completed", [])
            except json.JSONDecodeError:
                print("⚠️ Goal file is corrupt, resetting to empty.")
                self.goals = []
                self.completed = []
                self.save_goals()
        else:
            self.save_goals()

    def save_goals(self):
        try:
            with open(GOAL_FILE, "w") as f:
                json.dump({"goals": self.goals, "completed": self.completed}, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save goals file: {e}")

    def get_active_goals(self):
        """
        Return goals not completed and whose dependencies are met.
        Sorted by priority descending.
        """
        active = []
        completed_set = set(self.completed)
        for g in self.goals:
            if g.get("name") in completed_set:
                continue
            dependencies = g.get("dependencies", [])
            if all(dep in completed_set for dep in dependencies):
                active.append(g)
        active.sort(key=lambda g: g.get("priority", 0), reverse=True)
        return active

    def mark_complete(self, goal_name):
        for goal in self.goals:
            if goal.get("name") == goal_name and goal_name not in self.completed:
                self.completed.append(goal_name)
                goal["completed_at"] = datetime.now().isoformat()
                self.save_goals()
                print(f"✅ Goal marked complete: {goal_name}")
                print(f"🔍 Completed goals now: {self.completed}")  # DEBUG
                return goal
        print(f"⚠️ Goal not found or already completed: {goal_name}")
        print(f"🔍 Completed goals list: {self.completed}")  # DEBUG
        return None

    def assign_goal(self, goal):
        existing_names = [g.get("name") for g in self.goals]
        print(f"Existing goals when assigning new: {existing_names}")  # DEBUG
        if goal.get("name") in existing_names:
            print(f"⚠️ Goal '{goal.get('name')}' already assigned.")
            return None
        self.goals.append(goal)
        self.save_goals()
        print(f"✅ Goal assigned: {goal.get('name')}")
        return goal

    def create_goal_from_milestone(self, milestone_name, description, reward=5, priority=1, dependencies=None):
        if dependencies is None:
            dependencies = []
        goal = {
            "name": f"goal_for_{milestone_name}",
            "description": description,
            "reward": reward,
            "priority": priority,
            "dependencies": dependencies,
            "created_at": datetime.now().isoformat()
        }
        return self.assign_goal(goal)


if __name__ == "__main__":
    engine = GoalEngine()
    print("🎯 Active Goals:")
    for g in engine.get_active_goals():
        print(f"- {g['name']} (reward: {g.get('reward', 'N/A')})")