from datetime import datetime
import requests
from backend.config import GLYPH_API_BASE_URL

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

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
        memories = self.memory.get_all()
        recent = [m for m in memories if m["label"].startswith("dream_reflection_")][-limit:]

        print(f"[REFLECTION] Analyzing last {len(recent)} dream reflections...")

        reflections = []
        humility_delta = 0.0
        empathy_delta = 0.0
        curiosity_delta = 0.0
        ambition_delta = 0.0
        risk_delta = 0.0

        for m in recent:
            label = m.get("label", "unknown")
            content = m.get("content", "").lower()

            if "error" in content or "fail" in content:
                reflections.append(f"⚠️ Issue detected in '{label}'")
                humility_delta += 0.05
            elif "success" in content or "completed" in content:
                reflections.append(f"✅ Success noted in '{label}'")
                ambition_delta += 0.03
            elif "goal" in content or "strategy" in content:
                reflections.append(f"🎯 Goal-related memory: '{label}'")
                curiosity_delta += 0.02
            elif "others" in content or "help" in content:
                reflections.append(f"🫂 Cooperative tone in '{label}'")
                empathy_delta += 0.03
            else:
                preview = m.get("content", "")[:80].replace("\n", " ")
                reflections.append(f"🌀 General memory '{label}': {preview}...")
                empathy_delta += 0.01

            if "fear" in content or "risk" in content:
                risk_delta -= 0.03
            if "growth" in content or "vision" in content:
                ambition_delta += 0.04

        # Adjust traits in Personality Profile
        if humility_delta:
            self.personality.adjust_trait("humility", humility_delta)
        if empathy_delta:
            self.personality.adjust_trait("empathy", empathy_delta)
        if curiosity_delta:
            self.personality.adjust_trait("curiosity", curiosity_delta)
        if ambition_delta:
            self.personality.adjust_trait("ambition", ambition_delta)
        if risk_delta:
            self.personality.adjust_trait("risk_tolerance", risk_delta)

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

        # 🧬 Auto-synthesize glyphs from reflection insight
        try:
            print("🧠 Synthesizing glyphs from reflection insight...")
            res = requests.post(
                f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
                json={"text": insight_text, "source": "reflection"}
            )
            if res.status_code == 200:
                result = res.json()
                count = len(result.get("glyphs", []))
                print(f"✅ Synthesized {count} glyphs from insight.")
            else:
                print(f"⚠️ Glyph synthesis failed: {res.status_code} {res.text}")
        except Exception as e:
            print(f"🚨 Glyph synthesis error in ReflectionEngine: {e}")

    def run(self, limit: int = 10) -> str:
        """
        Main method: reflect, summarize, adjust traits, and store insights.
        Returns the generated reflection text.
        """
        reflections = self.reflect_on_recent_memories(limit=limit)
        combined = "\n".join(reflections)
        self.save_insight(combined)
        return combined


# ✅ Compatibility function used by glyph_executor and others
def generate_reflection(thought: str = "") -> str:
    """
    Externally callable function to trigger a reflection cycle.
    If a specific thought is passed, it can be stored beforehand.
    """
    engine = ReflectionEngine()
    return engine.run()