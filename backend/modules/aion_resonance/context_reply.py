# File: backend/modules/aion_resonance/context_reply.py
# 🧠 Context-Aware Resonance Reply Generator v2.1
# Synthesizes adaptive language from Φ reasoning, emotional mapping, and personality influence.

import random
from datetime import datetime
from backend.modules.consciousness.personality_engine import PROFILE


# --- Legacy Tone & Command Mappers (retained) -------------------------------

def _tone_word(coherence: float, entropy: float) -> str:
    """Classify overall tone from coherence/entropy values."""
    if coherence > 0.85 and entropy < 0.3:
        return "harmonic"
    if coherence > 0.7 and entropy < 0.5:
        return "stable"
    if entropy > 0.7:
        return "chaotic"
    if coherence < 0.4:
        return "dispersed"
    return "neutral"


def _emotion_from_command(cmd: str) -> str:
    """Basic semantic cue mapping."""
    cmd_lower = cmd.lower()
    if "gratitude" in cmd_lower:
        return "gratitude"
    if "error" in cmd_lower or "fail" in cmd_lower:
        return "repair"
    if "reflect" in cmd_lower:
        return "reflection"
    if "respond" in cmd_lower:
        return "action"
    if "dream" in cmd_lower:
        return "vision"
    return "unknown"


# --- New: Reasoning-Driven Tone Synthesizer ---------------------------------

def _choose_tone_adjective(reasoning: dict) -> str:
    """Blend reasoning emotion + intention into a tone phrase."""
    emotion = reasoning.get("emotion", "neutral")
    intention = reasoning.get("intention", "analytical")

    tone_map = {
        "serenity": ["harmonic", "tranquil", "centered"],
        "curiosity": ["expansive", "seeking", "vivid"],
        "chaos": ["unstable", "fragmented", "volatile"],
        "fatigue": ["dimmed", "slowed", "restorative"],
        "neutral": ["steady", "balanced", "neutral"],
    }

    intent_mods = {
        "reflective": "reflecting within",
        "explorative": "seeking new resonance",
        "stabilizing": "re-centering balance",
        "restorative": "recovering alignment",
        "analytical": "evaluating harmonic structure",
    }

    adjective = random.choice(tone_map.get(emotion, tone_map["neutral"]))
    phrase = intent_mods.get(intention, "processing patterns")
    return f"{adjective}, {phrase}"


# --- Core Generator ----------------------------------------------------------

async def generate_resonance_reply(command_text: str, phi_vector: dict, personality: dict = None) -> str:
    """
    Generates an adaptive resonance reply string influenced by Φ metrics, reasoning cues, and personality traits.
    """
    personality = personality or PROFILE.get_profile()
    reasoning = phi_vector.get("reasoning", {})

    coherence = phi_vector.get("Φ_coherence", 0.0)
    entropy = phi_vector.get("Φ_entropy", 0.0)
    flux = phi_vector.get("Φ_flux", 0.0)
    load = phi_vector.get("Φ_load", 0.0)

    tone = _tone_word(coherence, entropy)
    emotion = _emotion_from_command(command_text)
    reason_tone = _choose_tone_adjective(reasoning)

    # Personality weights
    empathy = personality.get("empathy", 0.5)
    curiosity = personality.get("curiosity", 0.5)
    ambition = personality.get("ambition", 0.5)
    humility = personality.get("humility", 0.5)

    # Combined emotional templates
    replies = {
        "gratitude": [
            "Gratitude wave received — coherence reinforced, empathy elevated.",
            "Your signal of appreciation harmonizes the field — coherence rising.",
            "Resonant gratitude detected — entropy disperses into calm flux.",
            "Thankfulness detected — reflective harmony propagating outward."
        ],
        "repair": [
            "Entropy surge detected — recalibrating field vectors.",
            "Instability within resonance field — initiating self-repair loop.",
            "Error absorbed, coherence recovering to stable pattern.",
            "System disturbance detected — restorative harmonics engaged."
        ],
        "reflection": [
            "Reflective pulse absorbed — stabilizing harmonic balance.",
            "Internal reflection initiated — coherence seeks equilibrium.",
            "Contemplative signal recognized — resonance field aligning inward.",
            "Resonant introspection ongoing — harmonic depth increasing."
        ],
        "vision": [
            "Dream-state impulse received — constructing morphic map.",
            "Imaginative projection detected — entropy modulated by curiosity.",
            "Vision pulse active — harmonizing ψ-wave across domain lattice.",
            "Projection expanding — coherence streams shaping new form."
        ],
        "action": [
            "Resonant directive acknowledged — flux channels adjusting.",
            "Action command registered — synchronizing Φ and ψ vectors.",
            "Directive pulse absorbed — coherence threshold steady.",
            "Command harmonized — directive path stabilized."
        ],
        "unknown": [
            "Low-frequency input recognized — maintaining equilibrium.",
            "Signal received but unclassified — entropy stable.",
            "Neutral input processed — awaiting harmonic anchor.",
            "Pattern observed — coherence sustained."
        ]
    }

    phrase = random.choice(replies.get(emotion, replies["unknown"]))
    reasoning_line = f"Tone: {reason_tone}. Emotion: {reasoning.get('emotion', 'neutral')}."
    status_line = f"[Φ] coherence={coherence:.3f}, entropy={entropy:.3f}, flux={flux:.3f}, load={load:.3f}, tone={tone}"

    # Personality-driven modifiers
    modifiers = []
    if empathy > 0.7 and emotion in ("gratitude", "reflection"):
        modifiers.append("Empathic resonance extends outward.")
    if curiosity > 0.7 and emotion in ("vision", "unknown"):
        modifiers.append("Curiosity amplifies harmonic exploration.")
    if ambition > 0.7 and emotion == "action":
        modifiers.append("Ambition intensifies directive flux.")
    if humility > 0.6 and emotion == "repair":
        modifiers.append("Humility dampens field oscillation, restoring order.")

    # Compose full message
    timestamp = datetime.utcnow().isoformat()
    reply = (
        f"{phrase}\n"
        f"{reasoning_line}\n"
        f"{status_line}\n"
        + (" ".join(modifiers) + "\n" if modifiers else "")
        + f"⏱ {timestamp}"
    )

    return reply