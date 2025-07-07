from backend.modules.skills.milestone_tracker import MilestoneTracker

# ✅ DNA Switch
from backend.modules.dna.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

tracker = MilestoneTracker()
tracker.unlock("memory_access")
print("Memory access unlocked:", tracker.is_unlocked("memory_access"))
