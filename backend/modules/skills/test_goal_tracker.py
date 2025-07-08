from goal_tracker import GoalTracker

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

tracker = GoalTracker()

print("🧠 Initial goals:", tracker.get_goals())

print("➕ Adding goal...")
tracker.add_goal("Enable autonomous economic simulations", "pending")

print("✅ Updated goals:", tracker.get_goals())

print("🟢 Marking as active...")
tracker.update_goal(0, "active")

print("🎯 Final state:", tracker.get_goals())
