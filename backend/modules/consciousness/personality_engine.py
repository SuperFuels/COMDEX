# File: backend/modules/consciousness/personality_engine.py

import json
import os
from datetime import datetime

# ✅ DNA Switch registration for symbolic tracking
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# 📁 Paths
TRAIT_FILE = "data/personality_traits.json"
HISTORY_FILE = "logs/personality_log.json"

# 🌱 Default traits if none stored yet
DEFAULT_TRAITS = {
    "curiosity": 0.7,
    "discipline": 0.5,
    "risk_tolerance": 0.4,
    "empathy": 0.6,
    "ambition": 0.8,
    "humility": 0.3
}

class PersonalityProfile:
    def __init__(self):
        self.traits = DEFAULT_TRAITS.copy()
        self.history = []

        if os.path.exists(TRAIT_FILE):
            with open(TRAIT_FILE, "r") as f:
                self.traits = json.load(f)

        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                self.history = json.load(f)

    def _save(self):
        os.makedirs(os.path.dirname(TRAIT_FILE), exist_ok=True)
        with open(TRAIT_FILE, "w") as f:
            json.dump(self.traits, f, indent=2)

        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history, f, indent=2)

    def adjust_trait(self, trait: str, delta: float, reason: str = "unspecified"):
        if trait in self.traits:
            prev = self.traits[trait]
            self.traits[trait] = max(0.0, min(1.0, prev + delta))
            self.history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "trait": trait,
                "delta": delta,
                "from": prev,
                "to": self.traits[trait],
                "reason": reason
            })
            print(f"[🧠] Trait '{trait}' changed: {prev:.2f} → {self.traits[trait]:.2f} ({reason})")
            self._save()
        else:
            print(f"[⚠️] Unknown trait: {trait}")

    def get_trait(self, trait: str) -> float:
        return self.traits.get(trait, 0.0)

    def get_profile(self) -> dict:
        return self.traits

    def has_required_traits(self, requirements: dict) -> bool:
        """
        Validate trait thresholds before allowing action.
        Example: { "discipline": 0.6, "humility": 0.4 }
        """
        for trait, threshold in requirements.items():
            value = self.traits.get(trait, 0.0)
            if value < threshold:
                print(f"[❌] Trait '{trait}' below threshold: {value:.2f} < {threshold:.2f}")
                return False
        return True

    def describe(self):
        print("\n🧬 AION Personality Profile:")
        for k, v in self.traits.items():
            bar = "█" * int(v * 20)
            print(f" - {k.capitalize():<14}: {v:.2f}  {bar}")
        print()

    def to_json(self) -> str:
        return json.dumps(self.traits, indent=2)

    def log_history(self):
        self._save()
        print("[📖] Personality history saved.")


# ✅ Singleton access
PROFILE = PersonalityProfile()

# ✅ External access shortcut
def get_current_traits():
    return PROFILE.traits