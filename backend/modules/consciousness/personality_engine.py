# backend/modules/consciousness/personality_engine.py

import json
import os
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

TRAIT_FILE = "data/personality_traits.json"
HISTORY_FILE = "logs/personality_log.json"

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

        # Load existing traits if saved
        if os.path.exists(TRAIT_FILE):
            with open(TRAIT_FILE, "r") as f:
                self.traits = json.load(f)

        # Load history if available
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

    def adjust_trait(self, trait, delta, reason: str = "unspecified"):
        if trait in self.traits:
            prev = self.traits[trait]
            self.traits[trait] = max(0.0, min(1.0, prev + delta))
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "trait": trait,
                "delta": delta,
                "from": prev,
                "to": self.traits[trait],
                "reason": reason
            }
            self.history.append(entry)
            print(f"[PERSONALITY] {trait} adjusted: {prev:.2f} → {self.traits[trait]:.2f} ({reason})")
            self._save()
        else:
            print(f"[PERSONALITY] Trait '{trait}' not recognized.")

    def get_profile(self) -> dict:
        return self.traits

    def describe(self):
        print("[PERSONALITY] Current trait profile:")
        for k, v in self.traits.items():
            bar = "#" * int(v * 10)
            print(f" - {k.capitalize():<14}: {v:.2f}  {bar}")

    def to_json(self) -> str:
        return json.dumps(self.traits, indent=2)

    def log_history(self):
        self._save()
        print(f"[PERSONALITY] History + traits saved to disk.")