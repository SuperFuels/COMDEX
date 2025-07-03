# File: modules/skills/dream_post_processor.py

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
        if not milestones:
            print("⚠️ No milestones found in dream.")
            milestones = []

        print(f"📍 Detected Milestones: {[m['type'] for m in milestones]}")

        # ✅ 2. Sync to Goal Engine
        goal_created = False
        for m in milestones:
            linked_goal = {
                "name": f"Unlock: {m['type']}",
                "description": m.get("summary", "Milestone triggered."),
                "reward": 20,
                "linked_milestone": m["type"]
            }
            self.goals.create_goal(linked_goal)
            print(f"🎯 Goal created: {linked_goal['name']}")
            goal_created = True

        # ✅ 3. Boot Skill Suggestion
        boot = self.boot_selector.find_matching_skill(dream)
        if boot:
            print(f"🚀 Boot Skill Matched: {boot['title']} | Tags: {', '.join(boot.get('tags', []))}")
        else:
            print("🛑 No boot skill matched from dream.")

        return {
            "milestones": milestones,
            "goal_created": goal_created,
            "boot_skill": boot
        }