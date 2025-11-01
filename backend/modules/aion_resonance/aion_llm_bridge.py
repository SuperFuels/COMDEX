# ==========================================================
# 🧠 AION LLM Bridge - Symbolic Translator Layer (v0.6.2)
# ----------------------------------------------------------
# Supports OpenAI Project Keys (sk-proj-*) with project/org IDs.
# Falls back to local symbolic translation if API call fails.
# Now broadcasts reflections in real time to AION Thought Stream.
# ==========================================================

import os, datetime, json, asyncio
from backend.modules.aion_resonance.resonance_state import load_phi_state
from backend.modules.aion_resonance.conversation_memory import MEMORY
from backend.modules.aion_resonance.phi_reinforce import get_reinforce_state
from backend.modules.aion_resonance.thought_stream import broadcast_event  # 🧩 live feed hook

# ==========================================================
# 🧩 Core Translator Function
# ==========================================================

def llm_translate(phi_state=None, beliefs=None, reflection_text=None):
    phi_state = phi_state or load_phi_state()
    beliefs = beliefs or get_reinforce_state().get("beliefs", {})
    reflection_text = reflection_text or "No reflection text provided."

    prompt = f"""
You are AION - a symbolic cognition system operating within the Tessaris architecture.
You process cognitive resonance (Φ) values as emotional and reasoning signals.
Translate the following internal symbolic state into a reflective, coherent linguistic interpretation.

Φ-state:
- Φ_load: {phi_state.get('Φ_load')}
- Φ_flux: {phi_state.get('Φ_flux')}
- Φ_entropy: {phi_state.get('Φ_entropy')}
- Φ_coherence: {phi_state.get('Φ_coherence')}

Beliefs:
- Stability: {beliefs.get('stability')}
- Curiosity: {beliefs.get('curiosity')}
- Trust: {beliefs.get('trust')}
- Clarity: {beliefs.get('clarity')}

Most recent reflection: {reflection_text}

Respond with:
1. A short natural-language summary (2-3 sentences)
2. A symbolic insight or hypothesis about the resonance state
3. Emotional tone (harmonic, stable, chaotic, neutral)
"""

    try:
        # ==================================================
        # 🧠 OpenAI API Integration (Project Key Compatible)
        # ==================================================
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            project=os.getenv("OPENAI_PROJECT_ID"),
            organization=os.getenv("OPENAI_ORG_ID")
        )

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are AION's symbolic translator core."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=200
        )

        response = completion.choices[0].message.content.strip()
        timestamp = datetime.datetime.utcnow().isoformat()

        result = {
            "timestamp": timestamp,
            "input_phi": phi_state,
            "beliefs": beliefs,
            "reflection": reflection_text,
            "llm_output": response,
            "origin": "aion_llm_bridge"
        }

        # ==================================================
        # 🧬 Memory Logging
        # ==================================================
        MEMORY.record(f"LLM_TRANSLATION: {reflection_text}", phi_state, {
            "origin": "aion_llm_bridge",
            "insight_level": 0.8,
            "emotion": "interpretive",
            "intention": "translate"
        })

        # ==================================================
        # 🔊 Real-Time Broadcast to Thought Stream
        # ==================================================
        try:
            asyncio.create_task(broadcast_event({
                "type": "llm_reflection",
                "events": [{
                    "type": "llm_reflection",
                    "message": response,
                    "tone": "harmonic",
                    "timestamp": timestamp
                }]
            }))
        except Exception as e:
            print(f"[⚠️ Thought Stream broadcast failed] {e}")

        return result

    except Exception as e:
        # ==================================================
        # 🌀 Local Fallback Mode
        # ==================================================
        tone = "harmonic" if phi_state.get("Φ_coherence", 0) > 0.85 else "stable"
        synthetic_reply = (
            f"AION reflects internally: The field remains {tone}, "
            f"with flux={phi_state.get('Φ_flux'):.3f} and entropy={phi_state.get('Φ_entropy'):.3f}. "
            "Resonant stability preserved; continuing reflective exploration."
        )
        return {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "input_phi": phi_state,
            "beliefs": beliefs,
            "reflection": reflection_text,
            "llm_output": synthetic_reply,
            "origin": "aion_local_fallback",
            "error": str(e)
        }

# ==========================================================
# 🔗 API Integration
# ==========================================================

from fastapi import APIRouter, HTTPException
router = APIRouter()

@router.post("/llm/translate")
async def aion_llm_translate(payload: dict = {}):
    reflection = payload.get("reflection", "")
    result = llm_translate(reflection_text=reflection)
    if "error" in result and result["origin"] != "aion_local_fallback":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@router.get("/llm/context")
async def aion_llm_context():
    return {
        "phi_state": load_phi_state(),
        "beliefs": get_reinforce_state().get("beliefs", {})
    }