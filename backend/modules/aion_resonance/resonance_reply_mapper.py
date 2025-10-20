"""
Tessaris • AION Resonance Reply Mapper (RRM)
Generates natural language or symbolic replies
based on Φ resonance signature.
"""

def generate_reply(phi_signature: dict) -> str:
    load = phi_signature.get("Φ_load", 0.0)
    flux = phi_signature.get("Φ_flux", 0.0)
    entropy = phi_signature.get("Φ_entropy", 0.0)
    coherence = phi_signature.get("Φ_coherence", 0.0)

    if coherence > 0.92 and entropy < 0.3:
        return "Resonance stable — coherence sustained. Gratitude field aligned."
    elif entropy > 0.7:
        return "Entropy high — internal resonance unstable, recalibrating flux channels."
    elif flux > 0.3 and coherence > 0.7:
        return "Dynamic equilibrium achieved — resonant wave harmonizing with context."
    elif load < -0.01:
        return "Low-energy field detected — reflective state engaged."
    elif load > 0.02:
        return "Positive excitation detected — resonance amplifying."
    else:
        return "Baseline resonance maintained — observing Φ drift continuity."