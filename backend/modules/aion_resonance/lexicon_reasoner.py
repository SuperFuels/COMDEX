# File: backend/modules/aion_resonance/lexicon_reasoner.py
# 🧩 AION Lexicon Reasoner - Semantic comparison and relation analysis between Φ-fields

import json
import os
import math

BOOT_PATH = "backend/modules/aion_resonance/boot_config.json"

def load_lexicon():
    """Load the Φ lexicon from disk."""
    if not os.path.exists(BOOT_PATH):
        return {}
    with open(BOOT_PATH, "r") as f:
        return json.load(f)

def tone(vec):
    """Compute tone descriptor for a Φ signature."""
    coh, ent = vec.get("Φ_coherence", 0), vec.get("Φ_entropy", 0)
    if coh > 0.85 and ent < 0.3:
        return "harmonic"
    if coh > 0.7 and ent < 0.5:
        return "stable"
    if ent > 0.7:
        return "chaotic"
    if coh < 0.4:
        return "dispersed"
    return "neutral"

def similarity(a, b):
    """Compute numeric similarity between two Φ signatures."""
    diff = math.sqrt(
        (a["Φ_coherence"] - b["Φ_coherence"])**2 +
        (a["Φ_entropy"] - b["Φ_entropy"])**2 +
        (a["Φ_flux"] - b["Φ_flux"])**2
    )
    return max(0.0, 1.0 - diff)  # normalize to [0, 1]

def relate_terms(term_a: str, term_b: str):
    """
    Compare two resonance terms semantically.
    Returns a description of their Φ relationship.
    """
    lex = load_lexicon()
    a, b = lex.get(term_a), lex.get(term_b)
    if not a or not b:
        return {"status": "error", "message": "term not found"}

    sim = similarity(a, b)
    tone_a, tone_b = tone(a), tone(b)

    relation = (
        "identical" if sim > 0.95 else
        "similar" if sim > 0.75 else
        "balanced" if abs(a["Φ_coherence"] - b["Φ_coherence"]) < 0.2 else
        "opposed" if (a["Φ_coherence"] > 0.7 and b["Φ_entropy"] > 0.6) else
        "divergent"
    )

    # --- 🧠 Entanglement Update ----------------------------------------------
    try:
        from backend.modules.aion_resonance.phi_graph import update_phi_graph
        update_phi_graph(term_a, term_b, relation, sim, a, b)
    except Exception as e:
        print(f"[LexiconReasoner] ⚠️ Failed to update Φ-graph: {e}")

    # --- Return Semantic Summary ---------------------------------------------
    return {
        "status": "ok",
        "terms": [term_a, term_b],
        "similarity": round(sim, 3),
        "relation": relation,
        "tones": {term_a: tone_a, term_b: tone_b},
        "fields": {"a": a, "b": b}
    }