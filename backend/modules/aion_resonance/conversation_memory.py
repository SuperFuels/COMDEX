# File: backend/modules/aion_resonance/conversation_memory.py
# 🧠 AION Conversational Working Memory — retains short-term Φ awareness
# Persists reasoning and resonance state between sessions

import json, os, datetime, statistics
from collections import deque

MEMORY_PATH = "data/conversation_memory.json"
MAX_MEMORY = 20  # retain last N thought-response cycles


class ConversationMemory:
    def __init__(self):
        self.history = deque(maxlen=MAX_MEMORY)
        os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)

        # Load persistent memory if available
        if os.path.exists(MEMORY_PATH):
            try:
                with open(MEMORY_PATH, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.history.extend(data)
            except Exception as e:
                print(f"[⚠️ MEMORY] Failed to load persisted memory: {e}")
                self.history.clear()

    def record(self, command: str, phi_state: dict, reasoning: dict):
        """Add a new Φ-memory entry with timestamp, command, Φ vector, and reasoning context."""
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "command": command,
            "phi": phi_state,
            "reasoning": reasoning,
        }
        self.history.append(entry)

        # Persist memory to disk
        try:
            with open(MEMORY_PATH, "w") as f:
                json.dump(list(self.history), f, indent=2)
        except Exception as e:
            print(f"[⚠️ MEMORY] Could not persist memory: {e}")

        coherence = phi_state.get("Φ_coherence", 0)
        print(f"[🧠 MEMORY] Recorded '{command}' | coherence={coherence:.3f}")

    def summarize(self):
        """Return recent Φ dynamics — coherence mean, entropy trend, etc."""
        if not self.history:
            return {}

        coherences = [e["phi"].get("Φ_coherence", 0) for e in self.history if "phi" in e]
        entropies = [e["phi"].get("Φ_entropy", 0) for e in self.history if "phi" in e]

        return {
            "count": len(self.history),
            "avg_coherence": round(statistics.mean(coherences), 4) if coherences else 0,
            "avg_entropy": round(statistics.mean(entropies), 4) if entropies else 0,
            "trend": "rising" if coherences[-1] > coherences[0] else "falling",
        }

    def get_recent(self):
        """Return recent conversation memory with summary."""
        return {
            "entries": list(self.history),
            "summary": self.summarize(),
        }


# 🌊 Global memory instance
MEMORY = ConversationMemory()