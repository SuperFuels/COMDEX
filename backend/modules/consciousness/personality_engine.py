# backend/modules/consciousness/personality_engine.py

import json
from datetime import datetime

class PersonalityProfile:
    def __init__(self):
        self.traits = {
            "curiosity": 0.7,       # Seeks novelty, learning
            "discipline": 0.5,      # Consistency and structure
            "risk_tolerance": 0.4,  # Willingness to take bold actions
            "empathy": 0.6,         # Care for others or external feedback
            "ambition": 0.8,        # Drive for growth/power
            "humility": 0.3         # Self-awareness and correction
        }
        self.history = []  # Log of changes for future learning loops

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

    def log_history(self, path: str = "logs/personality_log.json"):
        with open(path, "w") as f:
            json.dump(self.history, f, indent=2)
        print(f"[PERSONALITY] History logged to {path}")