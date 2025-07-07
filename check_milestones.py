from backend.modules.skills.milestone_tracker import MilestoneTracker

# ✅ DNA Switch
from backend.modules.dna.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

tracker = MilestoneTracker()
milestones = tracker.list_milestones()

print("🗓️ Milestones:")
if not milestones:
    print("  (no milestones)")
else:
    for m in milestones:
        print(f"- {m['name']} (source: {m.get('source')})")
