# ✅ TASK: Goal-linked milestone tracking with backend sync
# ✅ TASK: Boot skill loader from dream phrases

from modules.hexcore.memory_engine import MemoryEngine
from modules.skills.milestone_tracker import MilestoneTracker
from modules.skills.boot_selector import BootSelector
from modules.skills.goal_engine import GoalEngine

class DreamPostProcessor:
    """
    Processes a validated dream to:
    - Detect milestones
    - Trigger backend goal sync
    - Select boot skill based on keywords
    """

    def __init__(self):
        self.memory = MemoryEngine()
        self.tracker = MilestoneTracker()
        self.boot_selector = BootSelector()
        self.goals = GoalEngine()

    def process(self, dream: str):
        print("\n🔄 Post-processing dream...")

        # ✅ 1. Detect milestones
        milestones = self.tracker.detect_milestones_from_dream(dream)
        print(f"📍 Detected Milestones: {[m['type'] for m in milestones]}")

        # ✅ 2. Sync to Goal Engine
        for m in milestones:
            linked_goal = {
                "name": f"Unlock: {m['type']}",
                "description": m['summary'],
                "reward": 20,
                "linked_milestone": m['type']
            }
            self.goals.create_goal(linked_goal)
            print(f"🎯 Goal created: {linked_goal['name']}")

        # ✅ 3. Boot Skill Suggestion
        boot = self.boot_selector.select(dream)
        if boot:
            print(f"🚀 Boot Skill Matched: {boot['title']} | Tags: {', '.join(boot['tags'])}")
            return {
                "milestones": milestones,
                "goal_created": True,
                "boot_skill": boot
            }

        return {
            "milestones": milestones,
            "goal_created": True,
            "boot_skill": None
        }