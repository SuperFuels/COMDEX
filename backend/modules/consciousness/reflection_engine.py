from datetime import datetime
from modules.hexcore.memory_engine import MemoryEngine

class ReflectionEngine:
    def __init__(self):
        self.memory = MemoryEngine()

    def reflect_on_recent_memories(self, limit=10):
        memories = self.memory.get_all()[-limit:]
        print(f"[REFLECTION] Analyzing last {limit} memories...")

        reflections = []
        for m in memories:
            label = m.get("label", "unknown")
            content = m.get("content", "")
            if "error" in content.lower():
                reflections.append(f"⚠️ Caution: {label} had a problem.")
            elif "success" in content.lower():
                reflections.append(f"✅ Success noted in: {label}")
            else:
                reflections.append(f"🌀 Memory: {label} → {content[:100]}")

        return reflections

    def save_insight(self, text):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.memory.store({
            "label": f"reflection_insight_{timestamp}",
            "content": text
        })
        print(f"[REFLECTION] Insight saved: {text[:60]}...")

    def run(self):
        reflections = self.reflect_on_recent_memories()
        insight = "\n".join(reflections)
        self.save_insight(insight)
        return insight
