class PersonalityProfile:
    def __init__(self):
        self.traits = {
            "curiosity": 0.7,       # how much AION seeks new knowledge
            "discipline": 0.5,      # how consistently AION follows through
            "risk_tolerance": 0.4,  # how bold AION is with strategies
            "empathy": 0.6,         # weight AION gives to others' states
            "ambition": 0.8,        # how hard AION pushes to grow/power up
            "humility": 0.3         # ability to reflect on errors/failures
        }

    def adjust_trait(self, trait, delta):
        if trait in self.traits:
            self.traits[trait] = max(0.0, min(1.0, self.traits[trait] + delta))
            print(f"[PERSONALITY] {trait} adjusted to {self.traits[trait]:.2f}")
        else:
            print(f"[PERSONALITY] Trait '{trait}' not recognized.")

    def get_profile(self):
        return self.traits

    def describe(self):
        print("[PERSONALITY] Current trait profile:")
        for k, v in self.traits.items():
            bar = "#" * int(v * 10)
            print(f" - {k.capitalize():<14}: {v:.2f}  {bar}")
