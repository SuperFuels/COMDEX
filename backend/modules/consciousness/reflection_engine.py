#!/usr/bin/env python3
"""
🧠 ReflectionEngine — Phase 54: Resonant–Awareness Feedback Integration
───────────────────────────────────────────────────────────────
AION’s reflective loop now integrates with the harmonic field,
PersonalityProfile, and ResonantMemoryCache feedback.

Core Loop:
  • Analyzes recent dream_reflection memories
  • Computes ΔSQI harmonic pulse
  • Emits Θ.feedback("reflection", ΔΦ)
  • Pushes full harmonic sample into ResonantMemoryCache
  • Modulates PersonalityProfile using ΔSQI → emotional state
  • Logs resonance and insight to dashboard fields
"""

from datetime import datetime
import json, requests, random, time
from pathlib import Path
from statistics import mean

from backend.config import GLYPH_API_BASE_URL
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

DNA_SWITCH.register(__file__)

# ────────────────────────────────────────────────────────────────
class ReflectionEngine:
    def __init__(self):
        self.memory = MemoryEngine()
        self.personality = PersonalityProfile()
        self.insight_prefix = "reflection_insight"
        self.Θ = ResonanceHeartbeat(namespace="reflection", base_interval=1.2)
        self.RMC = ResonantMemoryCache()

        self.log_path = Path("data/analysis/reflection_resonance_log.jsonl")
        self.field_path = Path("data/analysis/reflection_field.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------
    def reflect_on_recent_memories(self, limit=10):
        memories = self.memory.get_all()
        recent = [m for m in memories if m["label"].startswith("dream_reflection_")][-limit:]
        print(f"[REFLECTION] Analyzing last {len(recent)} dream reflections...")

        reflections = []
        deltas = {"humility":0,"empathy":0,"curiosity":0,"ambition":0,"risk":0}

        for m in recent:
            label = m.get("label","unknown")
            content = m.get("content","").lower()

            if "error" in content or "fail" in content:
                reflections.append(f"⚠️ Issue detected in '{label}'")
                deltas["humility"] += 0.05
            elif "success" in content or "completed" in content:
                reflections.append(f"✅ Success noted in '{label}'")
                deltas["ambition"] += 0.03
            elif "goal" in content or "strategy" in content:
                reflections.append(f"🎯 Goal-related memory: '{label}'")
                deltas["curiosity"] += 0.02
            elif "others" in content or "help" in content:
                reflections.append(f"🫂 Cooperative tone in '{label}'")
                deltas["empathy"] += 0.03
            else:
                preview = m.get("content","")[:80].replace("\n"," ")
                reflections.append(f"🌀 General memory '{label}': {preview}...")
                deltas["empathy"] += 0.01

            if "fear" in content or "risk" in content:
                deltas["risk"] -= 0.03
            if "growth" in content or "vision" in content:
                deltas["ambition"] += 0.04

        # --- Update personality traits directly ---
        for k,v in deltas.items():
            if v:
                self.personality.adjust_trait(k, v, reason="reflection_pass")

        # --- Generate harmonic feedback sample ---
        rho = round(max(0.3, min(1.0, 0.7 + random.uniform(-0.1, 0.1))), 3)
        I = round(max(0.3, min(1.0, 0.6 + random.uniform(-0.1, 0.1))), 3)
        sqi = round((rho + I)/2, 3)
        delta_phi = round(abs(rho - I), 3)

        pulse = self.Θ.tick()
        pulse.update({
            "Φ_coherence": rho,
            "Φ_entropy": I,
            "SQI": sqi,
            "resonance_delta": delta_phi
        })

        # Derive mood from SQI delta
        mood_phase = "neutral"
        if sqi >= 0.75 and delta_phi < 0.15:
            mood_phase = "positive"
        elif sqi < 0.55 or delta_phi > 0.3:
            mood_phase = "negative"

        # Emit resonance feedback and push harmonic sample
        try:
            self.Θ.feedback("reflection", delta_phi)
            self.RMC.push_sample(rho=rho, entropy=I, sqi=sqi, delta=delta_phi, source="reflection")
            self.RMC.save()
        except Exception as e:
            print(f"[⚛] Reflection feedback error: {e}")

        # Feed ΔSQI into personality resonance modulator
        try:
            sqi_delta = sqi - 0.65  # relative to baseline coherence
            self.personality.resonant_trait_modulator(sqi_delta=sqi_delta, mood_phase=mood_phase)
        except Exception as e:
            print(f"[⚛] Personality modulation error: {e}")

        # Log detailed resonance event
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ρ": rho, "Ī": I, "SQI": sqi, "ΔΦ": delta_phi,
            "mood": mood_phase,
            "reflections": len(reflections)
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Append simplified trend field for dashboard
        with open(self.field_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": entry["timestamp"],
                "SQI": sqi,
                "ΔΦ": delta_phi,
                "mood": mood_phase
            }) + "\n")

        print(f"[Θ] Reflection feedback → ρ={rho:.3f}, Ī={I:.3f}, SQI={sqi:.3f}, ΔΦ={delta_phi:.3f}, mood={mood_phase}")
        return reflections

    # ------------------------------------------------------------
    def get_reflection_trend(self, window:int=50):
        """Compute rolling SQI and ΔΦ averages for dashboard aggregators."""
        if not self.field_path.exists():
            return {"avg_SQI":0, "avg_delta":0, "count":0, "mood":"neutral"}
        with open(self.field_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-window:]
        if not lines:
            return {"avg_SQI":0, "avg_delta":0, "count":0, "mood":"neutral"}
        data = [json.loads(l) for l in lines]
        sqi_vals = [d.get("SQI",0) for d in data]
        delta_vals = [d.get("ΔΦ",0) for d in data]
        moods = [d.get("mood","neutral") for d in data]
        dominant_mood = max(set(moods), key=moods.count) if moods else "neutral"
        return {
            "avg_SQI": round(mean(sqi_vals),3),
            "avg_delta": round(mean(delta_vals),3),
            "count": len(data),
            "mood": dominant_mood
        }

    # ------------------------------------------------------------
    def save_insight(self, insight_text:str):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        label = f"{self.insight_prefix}_{timestamp}"
        self.memory.store({"label":label, "content":insight_text})
        print(f"[REFLECTION] Insight saved under '{label}'")

        # Optional glyph synthesis
        try:
            res = requests.post(
                f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
                json={"text": insight_text, "source": "reflection"}
            )
            if res.status_code == 200:
                count = len(res.json().get("glyphs", []))
                print(f"✅ Synthesized {count} glyphs from insight.")
            else:
                print(f"⚠️ Glyph synthesis failed: {res.status_code}")
        except Exception as e:
            print(f"🚨 Glyph synthesis error: {e}")

    # ------------------------------------------------------------
    def run(self, limit:int=10) -> str:
        reflections = self.reflect_on_recent_memories(limit=limit)
        combined = "\n".join(reflections)
        self.save_insight(combined)
        return combined


# ────────────────────────────────────────────────────────────────
def generate_reflection(thought:str="") -> str:
    """External API: trigger a reflection cycle."""
    engine = ReflectionEngine()
    return engine.run()