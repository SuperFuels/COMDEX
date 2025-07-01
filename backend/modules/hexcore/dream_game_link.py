# modules/hexcore/dream_game_link.py

from modules.hexcore.memory_engine import MemoryEngine
from modules.aion.dream_core import DreamCore
from modules.hexcore.vision_core import VisionCore

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