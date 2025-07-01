from modules.skills.milestone_tracker import MilestoneTracker

tracker = MilestoneTracker()
tracker.display_progress()

# Example: Unlock a new module
# tracker.mark_milestone("Unlocked Nova Frontend", unlock_module="nova_frontend")
# tracker.display_progress()