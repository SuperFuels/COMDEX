# modules/hexcore/dream_game_link.py

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.aion.dream_core import DreamCore
from backend.modules.hexcore.vision_core import VisionCore

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class DreamGameLink:
    def __init__(self):
        self.memory = MemoryEngine()
        self.dream_core = DreamCore()
        self.vision = VisionCore()

    def run_game_dream_cycle(self):
        game_memories = self.memory.get_recent_entries(tags=["game_event"])
        insights = self.vision.extract_game_insights(game_memories)

        prompt = (
            "You are AION reflecting on your day in a Mario-like world. "
            "Here is what happened:\n"
            + "\n".join(insights) +
            "\nWhat lessons or feelings emerged from this?"
        )

        dream = self.dream_core.generate_dream(prompt=prompt)
        return dream