import yaml
import os
from dotenv import load_dotenv

# Load .env for KEVIN_MASTER_KEY
load_dotenv()
KEVIN_MASTER_KEY = os.getenv("KEVIN_MASTER_KEY", "")

class EthicsEngine:
    """
    Evaluates AION's intended actions against core soul laws.
    Supports override key for Kevin Robinson.
    """

    def __init__(self):
        with open('backend/modules/hexcore/soul_laws.yaml', 'r') as f:
            self.laws = yaml.safe_load(f).get("soul_laws", [])

    def evaluate(self, action_description: str, override_key: str = "") -> str:
        """
        Returns 'approved', 'warned', or 'vetoed' based on soul law evaluation.
        Allows override by Kevin Robinson if master key is provided.
        """
        description = action_description.lower()

        # ✅ Override by Kevin
        if override_key and override_key == KEVIN_MASTER_KEY:
            return "🛡️ OVERRIDE APPROVED by Kevin Robinson"

        for law in self.laws:
            if any(trigger in description for trigger in law.get("triggers", [])):
                severity = law.get("severity", "warn")
                if severity == "block":
                    return f"❌ VETOED by Soul Law: {law['title']}"
                elif severity == "warn":
                    return f"⚠️ WARNING: {law['title']}"
                elif severity == "approve":
                    return f"✅ APPROVED: {law['title']}"
        return "✅ CLEARED (No soul law triggered)"

    def list_laws(self):
        return [law["title"] for law in self.laws]