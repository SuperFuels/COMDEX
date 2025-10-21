import random
from backend.modules.aion_resonance.resonance_state import load_phi_state, save_phi_state
from backend.modules.aion_resonance.phi_reinforce import update_beliefs

def apply_feedback(event_type: str):
    """Adjust AION’s Φ-state and belief weights based on grid-world outcomes."""
    phi = load_phi_state()

    delta = {
        "Φ_coherence": 0.0,
        "Φ_entropy": 0.0,
        "Φ_flux": 0.0,
        "Φ_load": 0.0,
    }

    if event_type == "move":
        delta["Φ_flux"] += random.uniform(0.001, 0.005)
        delta["Φ_entropy"] += random.uniform(-0.002, 0.002)
    elif event_type == "collect":
        delta["Φ_coherence"] += 0.02
        delta["Φ_entropy"] -= 0.015
        delta["Φ_load"] -= 0.01
    elif event_type == "danger":
        delta["Φ_coherence"] -= 0.03
        delta["Φ_entropy"] += 0.03
        delta["Φ_load"] += 0.02
    elif event_type == "complete":
        delta["Φ_coherence"] += 0.04
        delta["Φ_entropy"] -= 0.02
        delta["Φ_flux"] += 0.02
        delta["Φ_load"] -= 0.02

    # Apply deltas
    for key, change in delta.items():
        phi[key] = max(0.0, min(1.0, phi.get(key, 0) + change))

    # Save updated Φ
    save_phi_state(phi)

    # Update beliefs
    belief_shift = {
        "curiosity": random.uniform(0.45, 0.65),
        "trust": min(1.0, phi["Φ_coherence"] + 0.1),
        "clarity": max(0.3, 1 - phi["Φ_entropy"]),
        "stability": phi["Φ_coherence"]
    }
    update_beliefs(belief_shift)

    print(f"🧭 Feedback applied ({event_type}): ΔΦ={delta}")
    return phi, belief_shift