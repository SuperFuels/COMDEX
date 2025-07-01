from goal_tracker import GoalTracker

tracker = GoalTracker()

print("🧠 Initial goals:", tracker.get_goals())

print("➕ Adding goal...")
tracker.add_goal("Enable autonomous economic simulations", "pending")

print("✅ Updated goals:", tracker.get_goals())

print("🟢 Marking as active...")
tracker.update_goal(0, "active")

print("🎯 Final state:", tracker.get_goals())
