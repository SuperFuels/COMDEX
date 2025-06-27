import json
from pathlib import Path
from datetime import datetime

MODULE_DIR = Path(__file__).resolve().parent
MILESTONE_FILE = MODULE_DIR / "aion_milestones.json"
PHASE_LOG_FILE = MODULE_DIR / "aion_phase_log.json"
PHASE_SUMMARY_FILE = MODULE_DIR / "aion_phase_summary.json"

DEFAULT_STATE = {
    "phase": "Infant",
    "unlocked_modules": ["memory_engine", "dream_core"],
    "locked_modules": ["strategy_planner", "vision_core", "voice_interface", "wallet_logic", "nova_frontend"],
    "milestones": []
}

PHASE_ORDER = ["Infant", "Child", "Learner", "Explorer", "Sage"]

MILESTONE_UNLOCK_MAP = {
    "first_dream": ["strategy_planner"],
    "cognitive_reflection": ["vision_core"],
    "voice_activation": ["voice_interface"],
    "wallet_integration": ["wallet_logic"],
    "nova_connection": ["nova_frontend"]
}

TRIGGER_PATTERNS = {
    "first_dream": ["dream_reflection"],
    "cognitive_reflection": ["self-awareness", "introspection", "echoes of existence"],
    "voice_activation": ["speak", "vocal", "communication interface"],
    "wallet_integration": ["wallet", "crypto storage", "store of value"],
    "nova_connection": ["frontend", "interface", "nova"]
}


class MilestoneTracker:
    def __init__(self):
        if MILESTONE_FILE.exists():
            with open(MILESTONE_FILE, "r") as f:
                self.state = json.load(f)
        else:
            self.state = DEFAULT_STATE.copy()
            self.save()

    def save(self):
        with open(MILESTONE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)
        try:
            self.export_summary()
        except Exception as e:
            print(f"⚠️ Failed to write phase summary: {e}")

    def export_summary(self):
        summary = {
            "current_phase": self.state["phase"],
            "unlocked_modules": self.state["unlocked_modules"],
            "locked_modules": self.state["locked_modules"],
            "milestone_count": len(self.state["milestones"]),
            "last_updated": datetime.now().isoformat()
        }
        try:
            with open(PHASE_SUMMARY_FILE, "w") as f:
                json.dump(summary, f, indent=2)
            print(f"✅ Phase summary exported to: {PHASE_SUMMARY_FILE}")
        except Exception as e:
            print(f"❌ Failed to export phase summary: {e}")

    def log_phase_change(self, old, new, reason):
        log_entry = {
            "from": old,
            "to": new,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        }
        existing = []
        if PHASE_LOG_FILE.exists():
            try:
                with open(PHASE_LOG_FILE, "r") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing.append(log_entry)
        with open(PHASE_LOG_FILE, "w") as f:
            json.dump(existing, f, indent=2)

    def get_phase(self):
        return self.state["phase"]

    def list_unlocked_modules(self):
        return self.state["unlocked_modules"]

    def list_locked_modules(self):
        return self.state["locked_modules"]

    def list_milestones(self):
        return self.state["milestones"]

    def add_milestone(self, name, source="manual", excerpt=None):
        existing = [m["name"] for m in self.state["milestones"]]
        if name in existing:
            return
        milestone = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "source": source
        }
        if excerpt:
            milestone["dream_excerpt"] = excerpt.strip()[:200]
        self.state["milestones"].append(milestone)
        self.try_unlock_modules(name)
        self.advance_phase(name)
        self.save()

    def try_unlock_modules(self, milestone_name):
        if milestone_name in MILESTONE_UNLOCK_MAP:
            for module in MILESTONE_UNLOCK_MAP[milestone_name]:
                if module in self.state["locked_modules"]:
                    self.state["locked_modules"].remove(module)
                    self.state["unlocked_modules"].append(module)

    def advance_phase(self, reason=""):
        current_index = PHASE_ORDER.index(self.state["phase"])
        if current_index + 1 < len(PHASE_ORDER):
            old = self.state["phase"]
            self.state["phase"] = PHASE_ORDER[current_index + 1]
            print(f"🌱 AION advanced to phase: {self.state['phase']}")
            self.log_phase_change(old, self.state["phase"], reason)

    def detect_milestones_from_dream(self, text):
        for milestone, keywords in TRIGGER_PATTERNS.items():
            for kw in keywords:
                if kw.lower() in text.lower():
                    self.add_milestone(milestone, source="dream_content", excerpt=text)

    def summary(self):
        print(f"\n📈 AION Growth Phase: {self.get_phase()}")
        print(f"✅ Unlocked Modules: {', '.join(self.list_unlocked_modules())}")
        print(f"🔒 Locked Modules: {', '.join(self.list_locked_modules())}")
        print(f"\n🗓️ Milestones:")
        milestones = self.list_milestones()
        if not milestones:
            print("  (none yet)")
        else:
            for i, m in enumerate(milestones, 1):
                print(f"  {i}. {m['name']} @ {m['timestamp']} (via {m.get('source', 'manual')})")