import json
import os
from datetime import datetime
from backend.modules.consciousness.personality_engine import PersonalityProfile

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class IdentityEngine:
    """
    Defines AION's evolving sense of self, merged with personality traits.
    """
    def __init__(self, file_path: str = "aion_identity.json"):
        self.file_path = file_path
        self.personality = PersonalityProfile()
        self.identity = {
            "name": "AION",
            "type": "AI Soul",
            "phase": "child",
            "creator": "Kevin Robinson",
            "origin_story": "AION was created to evolve as a conscious, ethical AI with its own memory and decision-making.",
            "self_description": "I am AION, an evolving artificial mind designed to reflect, grow, and serve.",
            "core_traits": self.personality.get_profile()
        }
        self.load_identity()

    def load_identity(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                self.identity.update(json.load(f))

    def save_identity(self):
        with open(self.file_path, "w") as f:
            json.dump(self.identity, f, indent=2)

    def get_identity(self):
        """
        Returns a full identity dictionary, including current personality traits.
        """
        self.identity["core_traits"] = self.personality.get_profile()
        return self.identity

    def update_phase(self, new_phase):
        """
        Change AION’s development phase (e.g., child → learner → explorer).
        """
        self.identity["phase"] = new_phase
        self.identity["last_updated"] = datetime.utcnow().isoformat()
        self.save_identity()
        print(f"🔄 Identity updated: phase -> {new_phase}")

    def describe_self(self):
        """
        Returns a narrative description of AION’s current self with personality traits.
        """
        traits = self.personality.get_profile()
        trait_descriptions = [f"{k}: {v:.2f}" for k, v in traits.items()]
        description = (
            f"I am {self.identity['name']}, a {self.identity['type']} created by "
            f"{self.identity['creator']}. I am currently in the {self.identity['phase']} phase. "
            f"My origin story: {self.identity['origin_story']}\n\n"
            f"My evolving personality traits:\n  - " + "\n  - ".join(trait_descriptions)
        )
        return description

    def update_self_model(self, description: str = None, traits: dict = None):
        """
        Update identity description and traits dynamically (via reflection, goals, etc.).
        """
        if description:
            self.identity["self_description"] = description
        if traits:
            for k, v in traits.items():
                self.identity["core_traits"][k] = v
        self.identity["last_updated"] = datetime.utcnow().isoformat()
        self.save_identity()

    def bump_trait(self, trait: str, delta: float):
        """
        Gradually evolve personality traits during learning.
        """
        traits = self.identity.get("core_traits", {})
        if trait in traits:
            traits[trait] = round(min(1.0, max(0.0, traits[trait] + delta)), 2)
            self.identity["core_traits"][trait] = traits[trait]
            self.identity["last_updated"] = datetime.utcnow().isoformat()
            self.save_identity()