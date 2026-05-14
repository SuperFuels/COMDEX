"""
Context ↔ AKG Bridge - Phase 43D
---------------------------------
Exports active conversation and emotional context
into the Aion Knowledge Graph (AKG).

This bridge forms the cognitive "snapshot layer" - each export represents
a temporal state of Aion's mind: what it is talking about, how it feels,
and how its resonance field is behaving.

Author: Tessaris Research Group
Date: Phase 43D - October 2025
"""

import time, json
from pathlib import Path
from backend.modules.aion_language.conversation_memory import MEM
from backend.modules.aion_language.semantic_context_manager import CTX
from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.bridges.photon_AKG_bridge import PAB


class ContextAKGBridge:
    """Bridge Aion's conversational context ↔ Photon AKG system."""

    def __init__(self):
        self.last_export = None
        self.path = Path("data/akg/context_exports.json")

    # ----------------------------------------------------------
    # 🧩 Core Aggregation
    # ----------------------------------------------------------
    def collect_context(self):
        """Aggregate current conversational, contextual, and emotional state."""
        # Extract last few entries safely
        events = getattr(MEM, "events", [])
        last_msgs = []
        if events and isinstance(events[-1], dict):
            last_msgs = [e.get("text", "") for e in events[-3:] if isinstance(e, dict)]

        context = {
            "timestamp": time.time(),
            "topics": getattr(CTX, "active_topics", []),
            "dominant_topic": getattr(CTX, "dominant_topic", None),
            "tone": getattr(TONE, "state", {}).get("tone", "neutral"),
            "energy": getattr(TONE, "state", {}).get("energy", 0.0),
            "confidence": getattr(TONE, "state", {}).get("confidence", 0.0),
            "recent_messages": last_msgs,
            "session_id": int(time.time()) // 3600,  # group exports hourly
        }

        # Derived values
        context["resonance_score"] = self.compute_resonance(context)
        context["coherence_index"] = self.compute_coherence(context)

        return context

    # ----------------------------------------------------------
    # 📊 Derived Metrics
    # ----------------------------------------------------------
    def compute_resonance(self, context):
        """Estimate resonance strength from tone energy and topic continuity."""
        continuity = len(context.get("topics", [])) / 5.0
        energy = context.get("energy", 0.0)
        return round((energy * 0.7) + (continuity * 0.3), 3)

    def compute_coherence(self, context):
        """Compute semantic coherence across tone + topic density."""
        topic_count = len(context.get("topics", []))
        conf = context.get("confidence", 0.0)
        if topic_count == 0:
            return 0.0
        return round(min(1.0, (conf * 0.6) + (topic_count / 10.0)), 3)

    # ----------------------------------------------------------
    # 🚀 Export & Persistence
    # ----------------------------------------------------------
    def export_to_AKG(self):
        """Collect and export context snapshot to the Photon AKG."""
        node = self.collect_context()
        self.last_export = node

        # Push live node into AKG system
        try:
            PAB.emit({"type": "context_snapshot", "target": "AKG", "payload": node})
        except Exception as e:
            print(f"[ContextAKGBridge] ⚠️ Failed to emit to PAB: {e}")

        # Local persistence
        self._save(node)

        print(
            f"[ContextAKGBridge] 📡 Exported context node -> AKG "
            f"(tone={node['tone']}, topic={node['dominant_topic']}, "
            f"resonance={node['resonance_score']})"
        )

        return node

    def _save(self, node):
        """Save export log locally for continuity and introspection."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            existing = json.load(open(self.path)) if self.path.exists() else []
        except Exception:
            existing = []
        existing.append(node)
        with open(self.path, "w") as f:
            json.dump(existing[-100:], f, indent=2)

    # ----------------------------------------------------------
    # 🧠 Review and Introspection
    # ----------------------------------------------------------
    def summarize_history(self, n=5):
        """Summarize the most recent N context exports."""
        if not self.path.exists():
            return {"summary": "No exports yet."}
        data = json.load(open(self.path))
        recent = data[-n:]
        tones = [d.get("tone", "neutral") for d in recent]
        avg_res = round(sum(d.get("resonance_score", 0.0) for d in recent) / len(recent), 3)
        return {
            "total_exports": len(data),
            "recent_tones": tones,
            "avg_resonance": avg_res,
            "last_export_time": recent[-1].get("timestamp", None),
        }


# 🔄 Global instance
try:
    CTX_AKG
except NameError:
    CTX_AKG = ContextAKGBridge()
    print("🌐 ContextAKGBridge global instance initialized as CTX_AKG")