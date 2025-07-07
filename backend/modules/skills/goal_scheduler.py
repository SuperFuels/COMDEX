import time
from backend.modules.skills.goal_runner import GoalRunner

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

def run_all_goals():
    runner = GoalRunner()
    active_goals = runner.engine.get_active_goals()
    print(f"🚀 Starting auto-run of {len(active_goals)} goals...\n")

    for goal in active_goals:
        print(f"⏳ Completing goal: {goal['name']}")
        try:
            runner.complete_goal(goal["name"])
            print(f"✅ Goal '{goal['name']}' completed successfully.\n")
        except Exception as e:
            print(f"❌ Failed to complete goal '{goal['name']}': {e}\n")
        time.sleep(2)  # Small delay between goals

if __name__ == "__main__":
    run_all_goals()