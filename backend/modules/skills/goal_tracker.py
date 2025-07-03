# backend/modules/skills/goal_tracker.py

import logging

logger = logging.getLogger("comdex")

class GoalTracker:
    def __init__(self):
        # In-memory goal store, use DB in prod
        self.goals = []
        self.next_id = 1

    def add_goal(self, name: str, status: str = "pending", description: str = None):
        """
        Add a new goal with name, status, and optional description.
        Returns the created goal dict.
        """
        # Check if goal already exists by name
        for goal in self.goals:
            if goal["name"].lower() == name.lower():
                logger.info(f"Goal already exists: {goal}")
                return goal
        
        goal = {
            "id": self.next_id,
            "name": name,
            "status": status,
            "description": description,
        }
        self.goals.append(goal)
        self.next_id += 1

        logger.info(f"Added goal: {goal}")
        return goal

    def create_goal(self, title: str, description: str = None):
        """
        Alias for add_goal to match route method name.
        """
        return self.add_goal(name=title, description=description)

    def list_goals(self):
        """
        Return all goals.
        """
        return self.goals

    def list_saved_goals(self):
        """
        Alias for list_goals to match route usage.
        """
        return self.list_goals()

    def get_goal_by_id(self, goal_id: int):
        """
        Retrieve a goal by its ID.
        """
        for goal in self.goals:
            if goal["id"] == goal_id:
                return goal
        return None

    def update_goal_status(self, goal_id: int, new_status: str):
        """
        Update status of a goal by ID.
        """
        goal = self.get_goal_by_id(goal_id)
        if goal:
            goal["status"] = new_status
            logger.info(f"Updated goal {goal_id} status to {new_status}")
            return goal
        logger.warning(f"Goal {goal_id} not found for update")
        return None

    def remove_goal(self, goal_id: int):
        """
        Remove a goal by ID.
        """
        old_len = len(self.goals)
        self.goals = [g for g in self.goals if g["id"] != goal_id]
        new_len = len(self.goals)
        logger.info(f"Removed goal {goal_id}, goals before: {old_len}, after: {new_len}")

    def add_goal_from_text(self, text_line: str):
        """
        Parse line 'Goal: Do something' and add goal.
        """
        if not text_line.lower().startswith("goal:"):
            return None
        parts = text_line.split(":", 1)
        if len(parts) < 2:
            return None
        goal_name = parts[1].strip()
        if not goal_name:
            return None
        return self.add_goal(goal_name)