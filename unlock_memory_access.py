frombackend.modules.skills.milestone_trackerimportMilestoneTracker

# ✅ DNA Switch
frombackend.modules.dna.dna_switchimportDNA_SWITCH
DNA_SWITCH.register(__file__)# Allow tracking + upgrades to this file

tracker=MilestoneTracker()
tracker.unlock("memory_access")
print("Memory access unlocked:",tracker.is_unlocked("memory_access"))
