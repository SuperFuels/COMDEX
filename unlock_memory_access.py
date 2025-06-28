from backend.modules.skills.milestone_tracker import MilestoneTracker

tracker = MilestoneTracker()
tracker.unlock("memory_access")
print("Memory access unlocked:", tracker.is_unlocked("memory_access"))
