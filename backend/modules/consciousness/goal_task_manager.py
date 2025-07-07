import random
from backend.modules.goals.goal_engine import GoalEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class GoalTaskManager:
    def __init__(self):
        self.goal_engine = GoalEngine()
        self.personality = PersonalityProfile()

    def prioritize_goals(self):
        """
        Adjust goal priorities based on personality traits like ambition, curiosity, and discipline.
        """
        traits = self.personality.get_profile()
        goals = self.goal_engine.get_all_goals()

        for goal in goals:
            base_priority = goal.get('priority', 1)
            if traits['ambition'] > 0.7:
                base_priority += 1
            if traits['curiosity'] > 0.6 and 'learn' in goal['name'].lower():
                base_priority += 1
            if traits['discipline'] < 0.4:
                base_priority -= 1
            goal['priority'] = max(1, base_priority)

        sorted_goals = sorted(goals, key=lambda g: g['priority'], reverse=True)
        return sorted_goals

    def get_next_task(self):
        """
        Return the highest-priority active goal.
        """
        prioritized = self.prioritize_goals()
        return prioritized[0] if prioritized else None

    def run_next_task(self):
        """
        Simulate execution of the top goal task and return the outcome.
        """
        task = self.get_next_task()
        if not task:
            return {"status": "no_goals", "message": "No active goals found."}

        result = {
            "goal": task['name'],
            "status": "in_progress",
            "confidence": round(random.uniform(0.6, 0.95), 2),
            "message": f"🎯 Working on goal: {task['name']} with priority {task['priority']}"
        }
        return result

# Optional CLI test
if __name__ == "__main__":
    mgr = GoalTaskManager()
    task = mgr.run_next_task()
    print(task)