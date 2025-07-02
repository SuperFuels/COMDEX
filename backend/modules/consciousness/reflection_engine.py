from datetime import datetime
from modules.hexcore.memory_engine import MemoryEngine
from modules.consciousness.personality_engine import PersonalityProfile

class ReflectionEngine:
    """
    The ReflectionEngine allows AION to analyze recent memory patterns
    and extract lessons or summaries as new insights.
    Adjusts personality traits like humility and empathy based on reflection content.
    """

    def __init__(self):
        self.memory = MemoryEngine()
        self.personality = PersonalityProfile()
        self.insight_prefix = "reflection_insight"

    def reflect_on_recent_memories(self, limit=10):
        """
        Analyze the latest N memories for insights, errors, and progress.
        Adjusts personality traits based on reflection content.
        Returns a list of reflection strings.
        """
        memories = self.memory.get_all()[-limit:]
        print(f"[REFLECTION] Analyzing last {limit} memories...")

        reflections = []
        humility_delta = 0.0
        empathy_delta = 0.0

        for m in memories:
            label = m.get("label", "unknown")
            content = m.get("content", "").lower()

            if "error" in content or "fail" in content:
                reflections.append(f"⚠️ Issue detected in '{label}'")
                humility_delta += 0.05  # Encourage humility on failures
            elif "success" in content or "completed" in content:
                reflections.append(f"✅ Success noted in '{label}'")
            elif "goal" in content or "strategy" in content:
                reflections.append(f"🎯 Goal-related memory: '{label}'")
            else:
                preview = m.get("content", "")[:80].replace("\n", " ")
                reflections.append(f"🌀 General memory '{label}': {preview}...")
                empathy_delta += 0.01  # Light increase in empathy for general reflection

        # Adjust traits based on total reflection tone
        if humility_delta > 0:
            self.personality.adjust_trait("humility", humility_delta)
        if empathy_delta > 0:
            self.personality.adjust_trait("empathy", empathy_delta)

        return reflections

    def save_insight(self, insight_text: str):
        """
        Save the combined reflection insight as a new memory.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        label = f"{self.insight_prefix}_{timestamp}"
        self.memory.store({
            "label": label,
            "content": insight_text
        })
        print(f"[REFLECTION] Insight saved under '{label}'")

    def run(self, limit: int = 10) -> str:
        """
        Main method: reflect, summarize, adjust traits, and store insights.
        Returns the generated reflection text.
        """
        reflections = self.reflect_on_recent_memories(limit=limit)
        combined = "\n".join(reflections)
        self.save_insight(combined)
        return combined