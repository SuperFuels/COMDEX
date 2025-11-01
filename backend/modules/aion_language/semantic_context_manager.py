"""
Semantic Context Manager - Phase 43B
------------------------------------
Maintains short-term and long-term conversational context windows.
Aggregates semantic + emotional continuity for reasoning across turns.

Author: Tessaris Research Group
Date: Phase 43B - October 2025
"""

import json, time
from pathlib import Path
from backend.modules.aion_language.conversation_memory import MEM

CTX_PATH = Path("data/context/semantic_context.json")

class SemanticContextManager:
    def __init__(self):
        self.short_term = []   # immediate context (recent turns)
        self.long_term = {}    # aggregated topic frequencies
        self.last_update = time.time()
        self._load()
        print("🧩 SemanticContextManager global instance initialized as CTX")

    def update_from_memory(self):
        """Sync short-term context from ConversationMemory."""
        recent = MEM.recall(5)
        self.short_term = []
        for entry in recent:
            topic = entry.get("semantic_field")
            emotion = entry.get("emotion_state")
            if topic:
                self.short_term.append({"topic": topic, "emotion": emotion})
                self.long_term[topic] = self.long_term.get(topic, 0) + 1
        self.last_update = time.time()
        self._save()
        print(f"[CTX] Updated short-term window with {len(self.short_term)} topics.")

    def summarize(self):
        """Return combined semantic + emotional summary."""
        if not self.short_term:
            self.update_from_memory()

        active_topics = [s["topic"] for s in self.short_term]
        dominant = max(self.long_term, key=self.long_term.get) if self.long_term else None

        summary = {
            "active_topics": list(dict.fromkeys(active_topics)),
            "dominant_topic": dominant,
            "context_age": round(time.time() - self.last_update, 2),
            "topic_counts": self.long_term,
        }
        return summary

    def recall_topic(self, keyword):
        """Check if a topic is active or historically known."""
        active = any(keyword in s["topic"] for s in self.short_term)
        known = keyword in self.long_term
        return {"active": active, "known": known, "frequency": self.long_term.get(keyword, 0)}

    def _save(self):
        CTX_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CTX_PATH, "w") as f:
            json.dump({
                "short_term": self.short_term,
                "long_term": self.long_term,
                "last_update": self.last_update,
            }, f, indent=2)

    def _load(self):
        if CTX_PATH.exists():
            try:
                with open(CTX_PATH) as f:
                    data = json.load(f)
                    self.short_term = data.get("short_term", [])
                    self.long_term = data.get("long_term", {})
                    self.last_update = data.get("last_update", time.time())
                print(f"[CTX] Loaded context with {len(self.long_term)} long-term topics.")
            except Exception as e:
                print(f"[CTX] ⚠️ Failed to load context: {e}")

# Global instance
try:
    CTX
except NameError:
    CTX = SemanticContextManager()