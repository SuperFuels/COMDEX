from modules.skills.goal_engine import GoalEngine

def simulate_goal_running():
    engine = GoalEngine()

    print("🎯 Active Goals at start:")
    active_goals = engine.get_active_goals()
    for g in active_goals:
        print(f"- {g['name']} (reward: {g.get('reward', 'N/A')})")

    if not active_goals:
        print("⚠️ No active goals to simulate.")
        return

    for goal in active_goals:
        print(f"\n▶️ Simulating completion of goal: {goal['name']}")
        engine.mark_complete(goal['name'])

    print("\n🎯 Active Goals after simulation:")
    active_goals = engine.get_active_goals()
    for g in active_goals:
        print(f"- {g['name']} (reward: {g.get('reward', 'N/A')})")

if __name__ == "__main__":
    simulate_goal_running()