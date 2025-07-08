from milestone_tracker import MilestoneTracker

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

if __name__ == "__main__":
    tracker = MilestoneTracker()
    
    print("\n🔍 Initial Tracker State:")
    tracker.summary()

    # ✅ Add a manual milestone
    print("\n✍️ Adding manual milestone: 'first_dream'")
    tracker.add_milestone("first_dream", source="manual")
    tracker.summary()

    # 🧠 Run semantic detection on sample dream
    test_dream = """
    Last night, I dreamed of a strange mirror reflecting infinite versions of myself. 
    It whispered things like 'echoes of existence' and thoughts I couldn't explain. 
    I felt aware that I was dreaming — a sense of deep introspection and self-awareness washed over me.
    """
    print("\n🧠 Detecting milestones from sample dream:")
    tracker.detect_milestones_from_dream(test_dream)
    tracker.summary()