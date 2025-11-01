frombackend.modules.skills.milestone_trackerimportMilestoneTracker

# ✅ DNA Switch
frombackend.modules.dna.dna_switchimportDNA_SWITCH
DNA_SWITCH.register(__file__)# Allow tracking + upgrades to this file

tracker=MilestoneTracker()
milestones=tracker.list_milestones()

print("🗓️ Milestones:")
ifnotmilestones:
    print("  (no milestones)")
else:
    forminmilestones:
        print(f"- {m['name']} (source: {m.get('source')})")
