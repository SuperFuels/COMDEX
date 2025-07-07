from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.goal_engine import GoalEngine

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

def create_goals_for_milestone(milestone_name):
    engine = GoalEngine()

    milestone_goal_map = {
        "first_dream": {
            "name": "explore_dreams",
            "description": "Analyze and catalog your first dream insights.",
            "reward": 10
        },
        "cognitive_reflection": {
            "name": "deepen_reflection",
            "description": "Perform a deeper reflection on cognitive processes.",
            "reward": 15
        },
        "voice_activation": {
            "name": "test_voice_interface",
            "description": "Implement and test voice communication capabilities.",
            "reward": 12
        },
        "wallet_integration": {
            "name": "secure_wallet_setup",
            "description": "Design and integrate secure wallet management.",
            "reward": 20
        },
        "nova_connection": {
            "name": "build_nova_frontend",
            "description": "Develop the frontend interface named Nova.",
            "reward": 25
        }
    }

    goal = milestone_goal_map.get(milestone_name)
    if goal:
        existing_names = [g.get("name") for g in engine.goals]
        if goal["name"] in existing_names:
            print(f"⚠️ Goal from milestone '{milestone_name}' already exists.")
            return
        assigned = engine.assign_goal(goal)
        if assigned:
            print(f"🎯 New goal assigned from milestone '{milestone_name}': {goal['name']}")
        else:
            print(f"⚠️ Goal from milestone '{milestone_name}' already exists.")

# Instantiate the tracker with the callback wired in
tracker = MilestoneTracker(goal_creation_callback=create_goals_for_milestone)
