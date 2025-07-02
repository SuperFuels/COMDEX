# File: modules/skills/boot_selector.py

import re
from modules.hexcore.memory_engine import MemoryEngine

class BootSelector:
    def __init__(self):
        self.memory = MemoryEngine()

    def extract_keywords(self, text: str):
        # Basic keyword extractor: split by space, filter short/common words
        words = re.findall(r"\b\w{4,}\b", text.lower())
        stopwords = {"from", "with", "this", "that", "there", "their", "about", "would", "could", "which", "while", "where"}
        return [w for w in words if w not in stopwords]

    def find_matching_skill(self, dream_text: str):
        keywords = set(self.extract_keywords(dream_text))
        queued_skills = [m for m in self.memory.get_all() if m.get("status") == "queued"]

        best_match = None
        max_overlap = 0

        for skill in queued_skills:
            tags = set(skill.get("tags", []))
            overlap = len(tags.intersection(keywords))

            if overlap > max_overlap:
                best_match = skill
                max_overlap = overlap

        if best_match:
            print(f"🔍 Dream keyword match found: {best_match['title']} ({max_overlap} keyword hits)")
            best_match["status"] = "in_progress"
            self.memory.update(best_match)
            return best_match

        print("🛑 No matching queued skill found from dream.")
        return None