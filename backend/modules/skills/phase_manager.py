import json
from datetime import datetime
from backend.modules.skills.milestone_goal_integration import tracker

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

PHASE_FILE = "backend/modules/skills/aion_phase_summary.json"

# Mapping of milestone keywords to modules they unlock
MODULE_TRIGGERS = {
    "strategic": "strategy_planner",
    "visual": "vision_core",
    "voice": "voice_interface",
    "wallet": "wallet_logic",
    "interface": "nova_frontend",
}

PHASES = [
    (0, "Seedling"),
    (1, "Infant"),
    (2, "Child"),
    (3, "Learner"),
    (4, "Explorer"),
    (5, "Strategist"),
    (6, "Sage"),
]


class PhaseManager:
    def __init__(self):
        self.tracker = tracker

    def get_current_phase(self, count):
        for threshold, name in reversed(PHASES):
            if count >= threshold:
                return name
        return "Seedling"

    def update_phase_summary(self):
        milestones = self.tracker.list_milestones()
        unlocked_modules = set(["memory_engine", "dream_core", "memory_access"])
        milestone_count = len(milestones)

        for m in milestones:
            name = m["name"].lower()
            for keyword, module in MODULE_TRIGGERS.items():
                if keyword in name:
                    unlocked_modules.add(module)

        locked_modules = [mod for mod in MODULE_TRIGGERS.values() if mod not in unlocked_modules]
        phase = self.get_current_phase(milestone_count)

        summary = {
            "current_phase": phase,
            "unlocked_modules": sorted(list(unlocked_modules)),
            "locked_modules": sorted(locked_modules),
            "milestone_count": milestone_count,
            "last_updated": datetime.now().isoformat()
        }

        with open(PHASE_FILE, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"✅ Phase summary exported to: {PHASE_FILE}")
