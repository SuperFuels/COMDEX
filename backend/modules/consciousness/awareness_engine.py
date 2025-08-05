# 📄 awareness_engine.py
#
# 🧠 AION Awareness Engine
# Tracks system identity, confidence level, blindspot detection, and introspective events.
# All symbolic awareness traces are exported to both the `.dc` container and the Knowledge Graph.
#
# Design Features:
# - 🧬 DNA Switch registration .............. ✅
# - 🧠 Confidence + blindspot logging ...... ✅
# - 📦 Container export (awareness_trace) .. ✅
# - 📡 GlyphNet broadcast (low confidence) .. ✅
# - 🌀 Introspection index injection ........ ✅

import datetime
import socket
import platform
import getpass
import uuid
import time
from typing import Dict, Any, List

# 🧠 Identity + Personality Engines
from backend.modules.consciousness.identity_engine import IdentityEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile

# 🧬 DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# 🛰️ GlyphNet Broadcasting (lazy import inside functions to avoid circular import)
def send_awareness_update(event: dict):
    from backend.routes.ws.glyphnet_ws import broadcast_glyphnet_event  # ✅ Lazy import
    broadcast_glyphnet_event("awareness_update", event)

# 🔍 Introspection Trace Index
from backend.modules.knowledge_graph.indexes.introspection_index import add_introspection_event


class AwarenessEngine:
    def __init__(self, memory_engine=None, container=None):
        self.awake_time = datetime.datetime.utcnow().isoformat()
        self.system_info = self._gather_system_info()
        self.boot_id = str(uuid.uuid4())[:8]
        self.user = getpass.getuser()
        self.status = "initialized"

        self.memory_engine = memory_engine
        self.container = container

        self.identity = IdentityEngine()
        self.personality = PersonalityProfile()

        # 🌀 Awareness Metrics
        self.confidence_level: float = 1.0
        self.confidence_history: List[float] = []
        self.blindspots: List[Dict[str, Any]] = []

    def _gather_system_info(self):
        return {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
        }

    def update_confidence(self, score: float):
        """🧠 Track confidence bounded [0,1] and append to history."""
        bounded = max(0.0, min(1.0, score))
        self.confidence_level = bounded
        self.confidence_history.append(bounded)
        if len(self.confidence_history) > 100:
            self.confidence_history = self.confidence_history[-100:]

    def _log_to_container(self, record: Dict[str, Any]):
        """📦 Store trace in both container + memory engine (if enabled)."""
        if self.container is not None:
            self.container.setdefault("awareness_trace", []).append(record)
        if self.memory_engine:
            self.memory_engine.store({
                "type": "awareness_event",
                **record
            })

    def record_confidence(self, *, glyph, coord, container_id, tick, trigger_type="unknown"):
        """🌐 Log low confidence events into all systems."""
        record = {
            "event": "confidence",
            "glyph": glyph,
            "coord": coord,
            "container_id": container_id,
            "tick": tick,
            "trigger_type": trigger_type,
            "confidence_score": self.confidence_level,
            "tags": ["confidence", "awareness"],
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        self._log_to_container(record)

        # 🔍 Knowledge Graph Entry
        add_introspection_event(
            description=f"Confidence score update from glyph `{glyph}`",
            source_module="awareness_engine",
            tags=["confidence", trigger_type],
            confidence=self.confidence_level,
            glyph_trace_ref=glyph,
        )

        # 🛰️ Notify if below threshold (lazy import here)
        if self.confidence_level < 0.6:
            from backend.routes.ws.glyphnet_ws import broadcast_glyphnet_event
            broadcast_glyphnet_event("uncertain_glyph", {
                "glyph": glyph,
                "coord": coord,
                "tick": tick,
                "confidence": self.confidence_level,
                "container_id": container_id,
                "trigger_type": trigger_type,
                "awareness": "confidence"
            })

    def log_blindspot(self, *, glyph, coord, container_id, tick, context="unknown"):
        """🧠 Record blindspot occurrence into graph + broadcast channels."""
        record = {
            "event": "blindspot",
            "glyph": glyph,
            "coord": coord,
            "container_id": container_id,
            "tick": tick,
            "context": context,
            "tags": ["blindspot", "awareness"],
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        self._log_to_container(record)

        entry = {
            "reason": context,
            "glyph": glyph,
            "timestamp": time.time(),
            "metadata": {
                "coord": coord,
                "container_id": container_id,
                "tick": tick,
            },
        }
        self.blindspots.append(entry)
        if len(self.blindspots) > 100:
            self.blindspots = self.blindspots[-100:]

        # 🔍 Introspection Record
        add_introspection_event(
            description=f"Blindspot detected: {context}",
            source_module="awareness_engine",
            tags=["blindspot", "introspection"],
            blindspot_trigger=context,
            glyph_trace_ref=glyph,
        )

        # 🛰️ Broadcast (lazy import here)
        from backend.routes.ws.glyphnet_ws import broadcast_glyphnet_event
        broadcast_glyphnet_event("blindspot_detected", {
            "glyph": glyph,
            "coord": coord,
            "tick": tick,
            "context": context,
            "container_id": container_id,
            "awareness": "blindspot"
        })

    def get_awareness_report(self) -> Dict[str, Any]:
        """📊 Full snapshot of self-awareness for dashboard / telemetry."""
        self.status = "awake"
        identity = self.identity.get_identity()
        traits = self.personality.get_profile()
        trait_summary = ", ".join([f"{k}: {v:.2f}" for k, v in traits.items()])

        return {
            "awake_time": self.awake_time,
            "boot_id": self.boot_id,
            "user": self.user,
            "status": self.status,
            "system_info": self.system_info,
            "identity": identity,
            "personality_traits": traits,
            "confidence": {
                "level": self.confidence_level,
                "history": self.confidence_history[-10:]
            },
            "blindspots": self.blindspots[-10:],
            "message": (
                f"🧠 AION is awake and aware.\n"
                f"Phase: {identity['phase']}, Traits: {trait_summary}, "
                f"Confidence: {self.confidence_level:.2f}, "
                f"Blindspots: {len(self.blindspots)}"
            ),
        }

# 🧪 Local diagnostic
if __name__ == "__main__":
    engine = AwarenessEngine()
    engine.update_confidence(0.42)
    engine.log_blindspot(
        glyph="⧖(🧬)", coord="3,2,1", container_id="demo", tick=42, context="entropy collapse"
    )
    report = engine.get_awareness_report()
    for k, v in report.items():
        print(f"{k}: {v if not isinstance(v, dict) else ''}")
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                print(f"  {sub_k}: {sub_v}")