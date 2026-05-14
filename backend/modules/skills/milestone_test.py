from backend.modules.skills.milestone_tracker import MilestoneTracker

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

tracker = MilestoneTracker()
tracker.display_progress()

# Example: Unlock a new module
# tracker.mark_milestone("Unlocked Nova Frontend", unlock_module="nova_frontend")
# tracker.display_progress()