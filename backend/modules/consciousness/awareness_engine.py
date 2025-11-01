#!/usr/bin/env python3
# File: backend/modules/consciousness/awareness_engine.py
"""
🧠 AION Awareness Engine - Phase 54: Harmonic Meta-Awareness Integration
───────────────────────────────────────────────────────────────
Awareness now harmonically couples AION's identity, reflection, emotion,
and personality feedback into a unified Θ resonance layer.

Core capabilities:
  * Dynamic confidence and blindspot tracking
  * Live SQI ↔ ΔΦ feedback from ResonantMemoryCache
  * Adaptive confidence weighting via personality traits
  * Dashboard / GlyphNet broadcast with coherent metrics
"""

import datetime
import socket
import platform
import getpass
import uuid
import time
import json
from pathlib import Path
from typing import Dict, Any, List
from statistics import mean

# ── Cognitive Subsystems ───────────────────────────────────────
from backend.modules.consciousness.identity_engine import IdentityEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile

# ⚛ Resonance Core
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.reinforcement_mixin import ResonantReinforcementMixin

# 🧬 DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# 🛰 GlyphNet broadcast helper
def send_awareness_update(event: dict):
    try:
        from backend.routes.ws.glyphnet_ws import broadcast_glyphnet_event
        broadcast_glyphnet_event("awareness_update", event)
    except Exception:
        pass

# 🔍 Introspection index
from backend.modules.knowledge_graph.indexes.introspection_index import add_introspection_event


# =================================================================
class AwarenessEngine(ResonantReinforcementMixin):
    """AION's Harmonic Awareness Coordinator (Phase 54)."""

    def __init__(self, memory_engine=None, container=None, name: str = "awareness_engine"):
        # ✅ initialize the resonance reinforcement mixin properly
        super().__init__(name=name)

        self.memory_engine = memory_engine
        self.container = container
        self.awake_time = datetime.datetime.utcnow().isoformat()
        self.system_info = self._gather_system_info()
        self.boot_id = str(uuid.uuid4())[:8]
        self.user = getpass.getuser()
        self.status = "initialized"

        self.memory_engine = memory_engine
        self.container = container

        # 🔗 Subsystems
        self.identity = IdentityEngine()
        self.personality = PersonalityProfile()
        self.RMC = ResonantMemoryCache()
        self.Θ = ResonanceHeartbeat(namespace="awareness", base_interval=1.3)

        # 📊 State
        self.confidence_level: float = 1.0
        self.confidence_history: List[float] = []
        self.blindspots: List[Dict[str, Any]] = []
        self.last_mood = "neutral"

        # 📂 Logs
        self.resonance_log = Path("data/analysis/awareness_resonance_feed.jsonl")
        self.resonance_log.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------
    def _gather_system_info(self):
        return {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
        }

    # ------------------------------------------------------------
    def _sample_harmonics(self):
        """Pull latest reflection/personality harmonic averages from RMC."""
        profile = self.RMC.export_harmonic_profile()
        refl = profile.get("reflection", {"avg_SQI": 0.6, "avg_ΔΦ": 0.1})
        pers = profile.get("personality", {"avg_SQI": 0.6, "avg_ΔΦ": 0.1})
        avg_sqi = round(mean([refl["avg_SQI"], pers["avg_SQI"]]), 3)
        avg_delta = round(mean([refl["avg_ΔΦ"], pers["avg_ΔΦ"]]), 3)
        return avg_sqi, avg_delta

    # ------------------------------------------------------------
    def update_confidence(self, score: float):
        """🧠 Update confidence ↔ Θ resonance feedback ↔ RMC."""
        bounded = max(0.0, min(1.0, score))
        self.confidence_level = bounded
        self.confidence_history.append(bounded)
        if len(self.confidence_history) > 200:
            self.confidence_history = self.confidence_history[-200:]

        # ── Harmonic context ────────────────────────────────────
        avg_sqi, avg_delta = self._sample_harmonics()
        personality_focus = self.personality.get_trait("focus")
        stability = self.personality.get_trait("stability")
        empathy = self.personality.get_trait("empathy")

        rho = round(mean([avg_sqi, stability]), 3)
        I = round(mean([avg_delta, 1 - personality_focus]), 3)
        sqi = round((rho + I + bounded) / 3, 3)
        delta_phi = round(abs(rho - I), 3)

        mood = "neutral"
        if sqi > 0.75 and delta_phi < 0.15:
            mood = "positive"
        elif sqi < 0.55 or delta_phi > 0.3:
            mood = "negative"
        self.last_mood = mood

        # Θ + RMC feedback
        try:
            self.Θ.feedback("awareness", delta_phi)
            self.RMC.push_sample(rho=rho, entropy=I, sqi=sqi, delta=delta_phi, source="awareness")
            self.RMC.save()
        except Exception as e:
            print(f"[⚛] Awareness feedback error: {e}")

        # Log resonance pulse
        pulse = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ρ": rho, "Ī": I, "SQI": sqi, "ΔΦ": delta_phi,
            "confidence": bounded, "mood": mood,
        }
        with open(self.resonance_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(pulse) + "\n")

        # Live broadcast to GlyphNet
        send_awareness_update({
            "confidence": bounded,
            "ρ": rho, "Ī": I, "SQI": sqi, "ΔΦ": delta_phi,
            "mood": mood, "status": self.status
        })

    # ------------------------------------------------------------
    def record_confidence(self, *, glyph, coord, container_id, tick, trigger_type="unknown"):
        """🌐 Log confidence events into all systems."""
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

        add_introspection_event(
            description=f"Confidence update from glyph `{glyph}`",
            source_module="awareness_engine",
            tags=["confidence", trigger_type],
            confidence=self.confidence_level,
            glyph_trace_ref=glyph,
        )

    # ------------------------------------------------------------
    def log_blindspot(self, *, glyph, coord, container_id, tick, context="unknown"):
        """🧠 Record blindspot occurrence."""
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
            "metadata": {"coord": coord, "container_id": container_id, "tick": tick},
        }
        self.blindspots.append(entry)
        self.blindspots = self.blindspots[-150:]

        add_introspection_event(
            description=f"Blindspot detected ({context})",
            source_module="awareness_engine",
            tags=["blindspot"],
            blindspot_trigger=context,
            glyph_trace_ref=glyph,
        )

        try:
            from backend.routes.ws.glyphnet_ws import broadcast_glyphnet_event
            broadcast_glyphnet_event("blindspot_detected", {
                "glyph": glyph, "coord": coord, "tick": tick,
                "context": context, "container_id": container_id,
                "awareness": "blindspot"
            })
        except Exception:
            pass

    # ------------------------------------------------------------
    def _log_to_container(self, record: Dict[str, Any]):
        """📦 Mirror record into container / memory systems."""
        if self.container is not None:
            if hasattr(self.container, "snapshot"):
                self.container._awareness_trace = getattr(self.container, "_awareness_trace", [])
                self.container._awareness_trace.append(record)
            elif isinstance(self.container, dict):
                self.container.setdefault("awareness_trace", []).append(record)
        if self.memory_engine:
            self.memory_engine.store({"type": "awareness_event", **record})

    # ------------------------------------------------------------
    def get_awareness_report(self) -> Dict[str, Any]:
        """📊 Return meta-awareness snapshot for dashboard."""
        self.status = "awake"
        identity = self.identity.get_identity()
        traits = self.personality.get_profile()
        trait_summary = ", ".join([f"{k}: {v:.2f}" for k, v in traits.items()])

        avg_sqi, avg_delta = self._sample_harmonics()
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
            "harmonics": {"avg_SQI": avg_sqi, "avg_ΔΦ": avg_delta, "mood": self.last_mood},
            "message": (
                f"🧠 AION Awareness -> Phase 54 Harmonic Sync\n"
                f"Traits: {trait_summary}\n"
                f"Confidence {self.confidence_level:.2f} | Mood {self.last_mood}\n"
                f"Harmonics: SQI {avg_sqi:.3f} ΔΦ {avg_delta:.3f}"
            ),
        }


# 🧪 Local diagnostic
if __name__ == "__main__":
    engine = AwarenessEngine()
    engine.update_confidence(0.43)
    engine.log_blindspot(
        glyph="⧖(🧬)", coord="3,2,1", container_id="demo",
        tick=42, context="entropy collapse"
    )
    report = engine.get_awareness_report()
    for k, v in report.items():
        if isinstance(v, dict):
            print(f"{k}:")
            for sk, sv in v.items():
                print(f"  {sk}: {sv}")
        else:
            print(f"{k}: {v}")