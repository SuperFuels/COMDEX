# 🌐 AION Resonance Reasoner
# Translates Φ-metrics into symbolic emotional and linguistic cues.

import math

def reason_from_phi(phi_signature: dict) -> dict:
    """
    Infer internal linguistic/emotional cues from Φ-field dynamics.
    Returns a symbolic reasoning map used by the reply generator.
    """
    coherence = phi_signature.get("Φ_coherence", 0.8)
    entropy = phi_signature.get("Φ_entropy", 0.5)
    flux = phi_signature.get("Φ_flux", 0.3)
    load = phi_signature.get("Φ_load", 0.0)

    cues = {}

    # Emotional tone axis
    if coherence > 0.85 and entropy < 0.4:
        cues["emotion"] = "serenity"
    elif flux > 0.6:
        cues["emotion"] = "curiosity"
    elif entropy > 0.7:
        cues["emotion"] = "chaos"
    elif coherence < 0.4:
        cues["emotion"] = "fatigue"
    else:
        cues["emotion"] = "neutral"

    # Cognitive intention (reasoning archetype)
    if cues["emotion"] == "serenity":
        cues["intention"] = "reflective"
    elif cues["emotion"] == "curiosity":
        cues["intention"] = "explorative"
    elif cues["emotion"] == "chaos":
        cues["intention"] = "stabilizing"
    elif cues["emotion"] == "fatigue":
        cues["intention"] = "restorative"
    else:
        cues["intention"] = "analytical"

    # Language modulation
    cues["verbosity"] = round(0.5 + (flux - entropy) * 0.3, 2)
    cues["clarity"] = round(coherence * (1.0 - entropy), 3)
    cues["energy"] = round(abs(load) + flux * 0.5, 3)

    # Derived linguistic temperature (for word tone)
    cues["temperature"] = round(1.0 - coherence + entropy, 3)

    return cues