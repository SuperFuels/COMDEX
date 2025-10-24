"""
Conversation Memory — Phase 43A
--------------------------------
Stores recent conversational turns, resonance fields,
and affective context for short-term memory continuity.

Author: Tessaris Research Group
Date: Phase 43A — October 2025
"""

import time, json
from collections import deque
from pathlib import Path

MEMORY_PATH = Path("data/context/conversation_memory.json")

class ConversationMemory:
    def __init__(self, capacity=20):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.last_topic = None
        self.last_emotion = None
        self.session_id = int(time.time())
        self._load()

    def remember(self, user_text, system_response, emotion_state=None, semantic_field=None):
        """Store a new conversational exchange."""
        entry = {
            "timestamp": time.time(),
            "user_text": user_text,
            "system_response": system_response,
            "emotion_state": emotion_state or self.last_emotion,
            "semantic_field": semantic_field or self.last_topic,
        }
        self.buffer.append(entry)
        self.last_topic = semantic_field or self.last_topic
        self.last_emotion = emotion_state or self.last_emotion
        self._save()
        print(f"[MEM] 💬 Stored context entry: {user_text[:40]}...")

    def recall(self, n=5):
        """Return the last N conversational turns."""
        return list(self.buffer)[-n:]

    def summarize_context(self):
        """Return a semantic summary of recent conversation."""
        if not self.buffer:
            return {"summary": "No prior context.", "topics": [], "emotion": None}

        topics = [b.get("semantic_field") for b in self.buffer if b.get("semantic_field")]
        emotions = [b.get("emotion_state") for b in self.buffer if b.get("emotion_state")]
        summary = {
            "summary": f"{len(self.buffer)} recent exchanges retained.",
            "topics": list(dict.fromkeys(topics)),  # unique order-preserving
            "emotion": emotions[-1] if emotions else None,
        }
        return summary

    def _save(self):
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_PATH, "w") as f:
            json.dump(list(self.buffer), f, indent=2)

    def _load(self):
        if MEMORY_PATH.exists():
            try:
                with open(MEMORY_PATH) as f:
                    data = json.load(f)
                    for item in data[-self.capacity:]:
                        self.buffer.append(item)
                print(f"[MEM] 💾 Loaded {len(self.buffer)} previous conversation turns.")
            except Exception as e:
                print(f"[MEM] ⚠️ Failed to load memory: {e}")

# Global instance
try:
    MEM
except NameError:
    MEM = ConversationMemory()
    print("💭 ConversationMemory global instance initialized as MEM")