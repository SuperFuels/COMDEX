import json
import logging
import threading

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

logger = logging.getLogger("comdex")
STORAGE_PATH = "backend/modules/skills/storage.json"

class GoalTracker:
    _lock = threading.Lock()

    def __init__(self):
        self.goals = []
        self.skills = []
        self.milestones = []
        self.next_id = 1
        self._load_storage()

    def _load_storage(self):
        try:
            with open(STORAGE_PATH, "r") as f:
                data = json.load(f)
            self.goals = data.get("goals", [])
            self.skills = data.get("skills", [
                {"name": "SkillA", "linked_goals": ["Goal 1"], "unlocked": False},
                {"name": "SkillB", "linked_goals": ["Goal 2"], "unlocked": False},
            ])
            self.milestones = data.get("milestones", [
                {"name": "MilestoneA", "linked_goals": ["Goal 1"], "unlocked": False},
                {"name": "MilestoneB", "linked_goals": ["Goal 2"], "unlocked": False},
            ])
            if self.goals:
                self.next_id = max(g.get("id", 0) for g in self.goals) + 1
            logger.info(f"Loaded storage: {len(self.goals)} goals, {len(self.skills)} skills, {len(self.milestones)} milestones")
        except FileNotFoundError:
            logger.warning("Storage file not found; starting with empty storage")
        except json.JSONDecodeError as e:
            logger.error(f"Storage JSON decode error: {e}")

    def _save_storage(self):
        with self._lock:
            data = {
                "goals": self.goals,
                "skills": self.skills,
                "milestones": self.milestones,
            }
            with open(STORAGE_PATH, "w") as f:
                json.dump(data, f, indent=2)
            logger.info("Saved storage to JSON")

    def add_goal(self, name: str, status: str = "pending", description: str = None):
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
        self._save_storage()
        return goal

    def create_goal(self, title: str, description: str = None):
        return self.add_goal(name=title, description=description)

    def list_goals(self):
        return self.goals

    def list_saved_goals(self):
        return self.list_goals()

    def get_goal_by_id(self, goal_id: int):
        for goal in self.goals:
            if goal["id"] == goal_id:
                return goal
        return None

    def update_goal_status(self, goal_id: int, new_status: str):
        goal = self.get_goal_by_id(goal_id)
        if goal:
            goal["status"] = new_status
            logger.info(f"Updated goal {goal_id} status to {new_status}")
            self._save_storage()
            return goal
        logger.warning(f"Goal {goal_id} not found for update")
        return None

    def remove_goal(self, goal_id: int):
        old_len = len(self.goals)
        self.goals = [g for g in self.goals if g["id"] != goal_id]
        new_len = len(self.goals)
        logger.info(f"Removed goal {goal_id}, goals before: {old_len}, after: {new_len}")
        self._save_storage()

    def add_goal_from_text(self, text_line: str):
        if not text_line.lower().startswith("goal:"):
            return None
        parts = text_line.split(":", 1)
        if len(parts) < 2:
            return None
        goal_name = parts[1].strip()
        if not goal_name:
            return None
        return self.add_goal(goal_name)

    def unlock_skills_for_goal(self, goal_name: str):
        unlocked_skills = []
        for skill in self.skills:
            if goal_name in skill.get("linked_goals", []) and not skill.get("unlocked", False):
                skill["unlocked"] = True
                unlocked_skills.append(skill["name"])
                logger.info(f"Skill unlocked: {skill['name']} for goal '{goal_name}'")
        self._save_storage()
        return unlocked_skills

    def unlock_milestones_for_goal(self, goal_name: str):
        unlocked_milestones = []
        for milestone in self.milestones:
            if goal_name in milestone.get("linked_goals", []) and not milestone.get("unlocked", False):
                milestone["unlocked"] = True
                unlocked_milestones.append(milestone["name"])
                logger.info(f"Milestone unlocked: {milestone['name']} for goal '{goal_name}'")
        self._save_storage()
        return unlocked_milestones