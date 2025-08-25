"""
🧠 emotion_engine.py

❤️ EmotionEngine – Symbolic Emotion Spike Recorder
Simulates emotional states and records symbolic glyphs when emotion spikes occur.

Design Rubric:
- ❤️ Emotion Tag + Intensity .................. ✅
- ⏱️ Tick + Timestamp Tracking ................ ✅
- 📦 Container-Aware Injection ................ ✅
- 🔁 Historical Spike Recall .................. ✅
- 🧠 Glyph Injection into Knowledge Graph ..... ✅
- ✅ DNA Switch Registration .................. ✅
"""

import random
import datetime
from typing import Optional

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ✅ Knowledge Graph Writer for emotion logging
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer 

# ✅ Updated time tracking (replaces deprecated time_engine)
from backend.modules.dimensions.time_controller import TimeController
TIME = TimeController()

def get_current_tick() -> int:
    """
    Proxy to maintain backward compatibility with existing calls.
    Fetches current tick from TimeController.
    """
    return TIME.get_current_tick()

class EmotionEngine:
    """
    Simulates emotional states and fluctuations based on events and input content.
    Emits symbolic glyphs when emotion spikes are detected.
    """

    def __init__(self):
        self.current_emotion = "neutral"
        self.history = []
        self.graph = get_kg_writer()

    def interpret_input(self, text: str) -> str:
        # Naive keyword-based sentiment interpretation
        text_lower = text.lower()
        positive = ["happy", "love", "hope", "excited", "grateful", "fun"]
        negative = ["sad", "hate", "fear", "angry", "pain", "alone"]

        if any(word in text_lower for word in positive):
            return "positive"
        elif any(word in text_lower for word in negative):
            return "negative"
        return "neutral"

    def shift_emotion(self, emotion: str, intensity: Optional[float] = None, trigger: Optional[str] = None):
        if emotion not in ["positive", "negative", "neutral"]:
            emotion = "neutral"
        self.current_emotion = emotion
        spike = {
            "emotion": emotion,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "tick": get_current_tick(),
            "intensity": intensity or round(random.uniform(0.2, 1.0), 2),
            "trigger": trigger or "unspecified"
        }
        self.history.append(spike)
        self.record_spike(spike)

    def record_spike(self, spike_data: dict):
        """
        H3a + H3c: Inject emotion spike glyph into the knowledge graph.
        """
        self.graph.inject_glyph(
            content=f"Emotion spike: {spike_data['emotion']}",
            glyph_type="emotion_spike",
            metadata={
                "intensity": spike_data["intensity"],
                "emotion": spike_data["emotion"],
                "trigger": spike_data["trigger"],
                "tick": spike_data["tick"]
            }
        )

    def get_emotion(self) -> str:
        return self.current_emotion

    def react_to_event(self, event: str):
        """
        Triggers emotion reaction and records spike.
        """
        emotion = "neutral"
        trigger = event
        if "failure" in event.lower() or "error" in event.lower():
            emotion = "negative"
        elif "success" in event.lower() or "reward" in event.lower():
            emotion = "positive"
        self.shift_emotion(emotion, trigger=trigger)

    def summarize_emotion_state(self) -> str:
        return f"Emotion: {self.current_emotion} | History Length: {len(self.history)}"