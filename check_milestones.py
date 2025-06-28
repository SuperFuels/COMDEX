from backend.modules.skills.milestone_tracker import MilestoneTracker

tracker = MilestoneTracker()
milestones = tracker.list_milestones()

print("🗓️ Milestones:")
if not milestones:
    print("  (no milestones)")
else:
    for m in milestones:
        print(f"- {m['name']} (source: {m.get('source')})")
