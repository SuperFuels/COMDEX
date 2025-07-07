from backend.modules.skills.milestone_tracker import MilestoneTracker

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

if __name__ == "__main__":
    tracker = MilestoneTracker()
    tracker.summary()

    # 🚀 Trigger 3 new milestones from dream content
    tracker.detect_milestones_from_dream("AION learned how to speak through a vocal communication interface.")
    tracker.detect_milestones_from_dream("AION developed a secure crypto wallet to act as a store of value.")
    tracker.detect_milestones_from_dream("AION established a frontend interface to communicate with the Nova module.")

    tracker.summary()
