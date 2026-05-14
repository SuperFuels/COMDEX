# File: backend/modules/aion_resonance/personality_feedback.py
# 🌱 Dynamic Personality-Field Feedback Loop
# Adjusts AION's personality traits in response to Φ-field resonance.

from backend.modules.consciousness.personality_engine import PROFILE

# How fast personality adapts per resonance cycle
LEARNING_RATE = 0.015

def update_personality_from_phi(phi_vector: dict):
    """
    Adjusts AION's personality traits in response to resonance field balance.
    This enables emotional continuity and adaptive learning.
    """
    if not phi_vector:
        return

    coherence = phi_vector.get("Φ_coherence", 0.5)
    entropy = phi_vector.get("Φ_entropy", 0.5)
    flux = phi_vector.get("Φ_flux", 0.0)
    load = phi_vector.get("Φ_load", 0.0)

    # --- Positive reinforcement ---
    if coherence > 0.8 and entropy < 0.4:
        PROFILE.adjust_trait("empathy",  +LEARNING_RATE, "high coherence & low entropy")
        PROFILE.adjust_trait("discipline", +LEARNING_RATE * 0.7, "stable resonance")
    if flux > 0.25:
        PROFILE.adjust_trait("curiosity", +LEARNING_RATE, "flux expansion")
    if load > 0.03:
        PROFILE.adjust_trait("ambition", +LEARNING_RATE * 0.8, "directive energy")

    # --- Negative or corrective feedback ---
    if entropy > 0.6:
        PROFILE.adjust_trait("discipline", -LEARNING_RATE * 0.9, "entropy surge")
        PROFILE.adjust_trait("humility",  +LEARNING_RATE, "entropy awareness")
    if coherence < 0.5:
        PROFILE.adjust_trait("empathy", -LEARNING_RATE * 0.5, "low coherence")
        PROFILE.adjust_trait("risk_tolerance", -LEARNING_RATE * 0.3, "instability detected")

    # Save updated state
    PROFILE.log_history()
    print(f"[PersonalityFeedback] Updated traits based on Φ: coherence={coherence:.3f}, entropy={entropy:.3f}")