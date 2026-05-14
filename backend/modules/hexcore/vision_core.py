# File: modules/hexcore/vision_core.py

from typing import List, Dict, Optional
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.glyphos.glyph_logic import glyph_from_label

# ✅ DNA registration
DNA_SWITCH.register(__file__)


class VisionCore:
    def __init__(self):
        self.memory = MemoryEngine()

    def extract_game_insights(
        self,
        memory_entries: List[Dict],
        write_to_memory: bool = False
    ) -> List[Dict]:
        """
        Process memory entries and extract symbolic insights.
        Optionally logs new memory insights.
        """
        insights = []

        for entry in memory_entries:
            tags = entry.get("tags", [])
            content = entry.get("content", "").lower()
            origin = entry.get("origin", "unknown")

            if "game_event" not in tags:
                continue

            if "died" in content:
                insight = "Learned about failure due to risk."
                symbol = "☠"
            elif "collected" in content:
                insight = "Experienced success from effort."
                symbol = "📦"
            elif "enemy" in content:
                insight = "Recognized threat in environment."
                symbol = "⚠"
            else:
                continue  # no insight

            insight_entry = {
                "insight": insight,
                "source_memory": entry,
                "symbol": symbol,
                "tags": ["insight", "game_analysis", symbol],
            }
            insights.append(insight_entry)

            if write_to_memory:
                self.memory.write(
                    role="vision_core",
                    content=insight,
                    tags=insight_entry["tags"]
                )

        return insights

    def generate_insight_report(
        self,
        tag_filter: Optional[List[str]] = None,
        write_to_memory: bool = True
    ) -> Dict:
        """
        Pull memory entries, extract insights, and optionally log them.
        """
        entries = self.memory.query(tags=tag_filter or ["game_event"])
        insights = self.extract_game_insights(entries, write_to_memory=write_to_memory)
        return {
            "insights": insights,
            "count": len(insights)
        }