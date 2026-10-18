# File: backend/modules/aion_resonance/conversation_memory.py
# 🧠 AION Conversational Working Memory - retains short-term Φ awareness
# Persists reasoning and resonance state between sessions

import json, datetime, statistics
from collections import deque
from pathlib import Path

from backend.modules.aion_learning.vault_store import AionLearningVaultStore

MEMORY_PATH = Path("data/conversation_memory.json")
MAX_MEMORY = 20  # retain last N thought-response cycles


class ConversationMemory:
    def __init__(
        self,
        *,
        memory_path: str | Path | None = None,
        vault_store: AionLearningVaultStore | None = None,
        max_memory: int = MAX_MEMORY,
    ):
        self.memory_path = Path(memory_path or MEMORY_PATH)
        self.vault_store = vault_store or AionLearningVaultStore(
            auto_configure=memory_path is None
        )
        self.history = deque(maxlen=max(1, int(max_memory)))

        # Load persistent memory if available
        try:
            if self.vault_store.enabled:
                payload = self.vault_store.get_state(
                    "conversation_memory", {"entries": []}
                )
                data = payload.get("entries", []) if isinstance(payload, dict) else []
            elif self.memory_path.exists():
                with open(self.memory_path, "r") as f:
                    data = json.load(f)
            else:
                data = []
            if isinstance(data, list):
                self.history.extend(data)
        except Exception as e:
            print(f"[⚠️ MEMORY] Failed to load persisted memory: {e}")
            self.history.clear()

    def record(self, command: str, phi_state: dict, reasoning: dict):
        """Add a new Φ-memory entry with timestamp, command, Φ vector, and reasoning context."""
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "command": command,
            "phi": phi_state,
            "reasoning": reasoning,
        }
        self.history.append(entry)

        # Persist memory to disk
        try:
            if self.vault_store.enabled:
                self.vault_store.put_state(
                    "conversation_memory", {"entries": list(self.history)}
                )
            else:
                self.memory_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.memory_path, "w") as f:
                    json.dump(list(self.history), f, indent=2)
        except Exception as e:
            print(f"[⚠️ MEMORY] Could not persist memory: {e}")

        coherence = phi_state.get("Φ_coherence", 0)
        print(f"[🧠 MEMORY] Recorded '{command}' | coherence={coherence:.3f}")

    def summarize(self):
        """Return recent Φ dynamics - coherence mean, entropy trend, etc."""
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

    def load(self):
        """Compatibility read used by the Thought Stream route."""
        return list(self.history)


# 🌊 Global memory instance
MEMORY = ConversationMemory()
