import re
from backend.modules.hexcore.memory_engine import MemoryEngine

class BootSelector:
    def __init__(self):
        self.memory = MemoryEngine()

    def extract_keywords(self, text: str):
        """
        Basic keyword extractor: uses regex to find words longer than 3 characters,
        and filters out common stopwords.
        """
        words = re.findall(r"\b\w{4,}\b", text.lower())
        stopwords = {
            "from", "with", "this", "that", "there", "their",
            "about", "would", "could", "which", "while", "where"
        }
        return [w for w in words if w not in stopwords]

    def find_matching_skill(self, dream_text: str, triggered_by_strategy_id=None, triggered_by_goal=None):
        """
        Compares extracted keywords from the dream text with queued skills in memory.
        The skill with the most tag overlaps is selected and marked as 'in_progress'.
        Additionally, records which strategy or goal triggered the skill selection.
        """
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
            # Store trigger metadata for traceability
            if triggered_by_strategy_id:
                best_match["triggered_by_strategy_id"] = triggered_by_strategy_id
            if triggered_by_goal:
                best_match["triggered_by_goal"] = triggered_by_goal
            self.memory.update(best_match)
            return best_match

        print("🛑 No matching queued skill found from dream.")
        return None

    def select(self, dream_text: str, triggered_by_strategy_id=None, triggered_by_goal=None):
        """
        Wrapper to keep external API consistent.
        """
        return self.find_matching_skill(dream_text, triggered_by_strategy_id, triggered_by_goal)