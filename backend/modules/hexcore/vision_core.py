# modules/hexcore/vision_core.py

from modules.hexcore.memory_engine import MemoryEngine

class VisionCore:
    def __init__(self):
        self.memory = MemoryEngine()

    def extract_game_insights(self, memory_entries):
        insights = []
        for entry in memory_entries:
            if "game_event" in entry["tags"]:
                content = entry["content"].lower()
                if "died" in content:
                    insights.append("Learned about failure due to risk.")
                elif "collected" in content:
                    insights.append("Experienced success from effort.")
                elif "enemy" in content:
                    insights.append("Recognized threat in environment.")
        return insights