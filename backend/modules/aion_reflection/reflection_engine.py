#!/usr/bin/env python3
"""
🧠 ReflectionEngine - Phase 63: Bidirectional Θ-Coupled Resonant Reflection
───────────────────────────────────────────────────────────────
Completes the Reflection Engine within the Resonant Governance Cycle.
Integrates with Θ.sync_all(), Harmonic Memory Fusion (HMF),
and the Resonant Integration Bridge (RIB).

Core Loop:
  * Analyzes recent dream_reflection memories
  * Computes Δρ, ΔĪ, ΔSQI + ΔH (Harmony delta)
  * Emits Θ.event("reflection_feedback", ...)
  * Pushes harmonic sample into Resonant Memory Cache
  * Modulates Personality Profile via resonance mood
  * Logs reflection + harmony feedback to dashboard
"""

import json, time, random, requests
from datetime import datetime
from pathlib import Path
from statistics import mean

from backend.config import GLYPH_API_BASE_URL
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.dna_chain.switchboard import DNA_SWITCH

DNA_SWITCH.register(__file__)


class ReflectionEngine:
    def __init__(self):
        self.memory = MemoryEngine()
        self.personality = PersonalityProfile()
        self.RMC = ResonantMemoryCache()
        self.Theta = ResonanceHeartbeat(namespace="reflection", base_interval=1.2)

        # Paths
        self.log_path = Path("data/analysis/reflection_resonance_log.jsonl")
        self.field_path = Path("data/analysis/reflection_field.jsonl")
        self.hm_path = Path("data/analysis/harmonic_memory.json")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------
    def _get_last_harmony(self):
        """Return the last harmony_integral from harmonic_memory.json"""
        try:
            if self.hm_path.exists():
                js = json.loads(self.hm_path.read_text())
                return float(js.get("harmony_integral", 0.5))
        except Exception:
            pass
        return 0.5

    # ------------------------------------------------------------
    def reflect_on_recent_memories(self, limit=10):
        memories = self.memory.get_all()
        recent = [m for m in memories if m["label"].startswith("dream_reflection_")][-limit:]
        print(f"[REFLECTION] Analyzing last {len(recent)} reflection memories...")

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

        # Text sentiment is advisory only.  It cannot mutate personality or
        # become a retained lesson without a verified action outcome.

        # --- Resonance sampling ---
        rho = round(random.uniform(0.45, 0.9), 3)
        I = round(random.uniform(0.4, 0.8), 3)
        sqi = round((rho + (1 - I)) / 2, 3)
        delta_phi = round(abs(rho - I), 3)

        # Harmony delta vs last global harmonic memory
        last_H = self._get_last_harmony()
        current_H = 1 - delta_phi
        delta_H = round(current_H - last_H, 3)

        # --- Mood state ---
        mood_phase = "neutral"
        if sqi >= 0.75 and delta_phi < 0.15:
            mood_phase = "positive"
        elif sqi < 0.55 or delta_phi > 0.3:
            mood_phase = "negative"

        # --- Heartbeat emission + RMC push ---
        try:
            self.Theta.event("reflection_feedback",
                             sqi=sqi, entropy=I, delta=delta_phi,
                             harmony_delta=delta_H, mood=mood_phase)
            self.RMC.push_sample(rho=rho, entropy=I, sqi=sqi, delta=delta_phi, source="reflection")
            self.RMC.save()

            # --- Feedback coupling -> Motivation Layer ---
            try:
                from backend.modules.aion_cognition.motivation_layer import MotivationLayer
                motive = MotivationLayer()
                feedback_payload = {
                    "Δρ": delta_phi,
                    "ΔSQI": sqi - self.RMC.get("last_sqi", 0.65) if hasattr(self.RMC, "get") else sqi - 0.65,
                    "entropy": I,
                    "ΔH": delta_H
                }
                motive.update_from_reflection(feedback_payload)
                print(f"[ReflectionEngine] ⚡ Sent feedback to MotivationLayer -> {feedback_payload}")
            except Exception as e:
                print(f"[ReflectionEngine] ⚠️ Motivation feedback link failed: {e}")

        except Exception as e:
            print(f"[⚛] Resonant feedback error: {e}")

        # Resonance remains useful telemetry, but has no identity, learning or
        # execution authority.

        # --- Logging ---
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "ρ": rho, "Ī": I, "SQI": sqi, "ΔΦ": delta_phi,
            "ΔH": delta_H, "mood": mood_phase,
            "reflections": len(reflections)
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        with open(self.field_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": entry["timestamp"],
                "SQI": sqi, "ΔΦ": delta_phi,
                "ΔH": delta_H, "mood": mood_phase
            }) + "\n")

        print(f"[Θ] Reflection -> ρ={rho:.3f}, Ī={I:.3f}, SQI={sqi:.3f}, ΔΦ={delta_phi:.3f}, ΔH={delta_H:.3f}, mood={mood_phase}")
        # ─────────────────────────────────────────────────────────────
        # 🔄 Integrate Photon Memory Grid feedback (ΔSQI / ΔH)
        # ─────────────────────────────────────────────────────────────
        try:
            from backend.modules.aion.reflection_feedback import AION_FEEDBACK
            feedback = AION_FEEDBACK.compute_feedback()
            print(f"[PMG↔Aion] ΔSQI={feedback['ΔSQI']:+.4f} ΔH={feedback['ΔH']:+.4f} "
                  f"(coh={feedback['avg_coherence']:.3f}, ent={feedback['avg_entropy']:.3f})")
        except Exception as e:
            print(f"[PMG↔Aion] ⚠️ Feedback integration failed: {e}")
        return reflections

    # ------------------------------------------------------------
    def get_reflection_trend(self, window:int=50):
        if not self.field_path.exists():
            return {"avg_SQI":0,"avg_delta":0,"avg_harmony":0,"count":0,"mood":"neutral"}
        with open(self.field_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-window:]
        if not lines:
            return {"avg_SQI":0,"avg_delta":0,"avg_harmony":0,"count":0,"mood":"neutral"}
        data = [json.loads(l) for l in lines]
        sqis = [d.get("SQI",0) for d in data]
        deltas = [d.get("ΔΦ",0) for d in data]
        harmonies = [d.get("ΔH",0) for d in data]
        moods = [d.get("mood","neutral") for d in data]
        dom_mood = max(set(moods), key=moods.count) if moods else "neutral"
        return {
            "avg_SQI": round(mean(sqis),3),
            "avg_delta": round(mean(deltas),3),
            "avg_harmony": round(mean(harmonies),3),
            "count": len(data),
            "mood": dom_mood
        }

    # ------------------------------------------------------------
    def save_insight(self, insight_text:str, *, synthesize_glyphs: bool = False):
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        label = f"reflection_insight_{ts}"
        self.memory.store({"label":label,"content":insight_text})
        print(f"[REFLECTION] Insight saved as '{label}'")

        # Glyph synthesis is opt-in and remains proposal-only.  Automatic HTTP
        # promotion previously allowed an unverified reflection to masquerade
        # as knowledge.
        if not synthesize_glyphs:
            return {"label": label, "stored_as": "unverified_reflection", "glyphs_promoted": 0}
        try:
            res = requests.post(f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
                                json={"text": insight_text, "source": "reflection"})
            if res.status_code == 200:
                count = len(res.json().get("glyphs", []))
                print(f"✅ Synthesized {count} glyphs from insight.")
            else:
                print(f"⚠️ Glyph synthesis failed: {res.status_code}")
        except Exception as e:
            print(f"🚨 Glyph synthesis error: {e}")

    def reflect_on_outcome(
        self,
        *,
        goal: dict,
        plan: dict,
        action: dict,
        review: dict,
        action_result: dict,
        observation: dict,
        criticism: dict,
    ) -> dict:
        """Delegate real learning to AION's outcome-grounded metacognition."""
        from backend.modules.hexcore.metacognitive_control import MetacognitiveController

        result = MetacognitiveController().reflect_outcome(
            goal=goal,
            plan=plan,
            action=action,
            review=review,
            action_result=action_result,
            observation=observation,
            criticism=criticism,
        )
        result["legacy_resonance_authority"] = False
        result["knowledge_promotion_requires_verified_outcome"] = True
        return result

    # ------------------------------------------------------------
    def run(self, limit:int=10):
        reflections = self.reflect_on_recent_memories(limit)
        insight = "\n".join(reflections)
        self.save_insight(insight)
        return insight


# ────────────────────────────────────────────────────────────────
def generate_reflection(thought:str="") -> str:
    """External trigger for full reflection cycle."""
    engine = ReflectionEngine()
    return engine.run()

if __name__ == "__main__":
    engine = ReflectionEngine()
    print("🧠 Running ReflectionEngine full cycle (Phase 63)...")
    engine.run(limit=5)
