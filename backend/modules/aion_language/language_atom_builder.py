"""
LanguageAtomBuilder — Phase 37B : Language Atom Genesis
--------------------------------------------------------
Transforms meaning clusters (from MFG) into Language Atoms:
  • center → concept anchor
  • lexeme → synthetic linguistic handle
  • glyphs → symbolic associations (Φ ⊕ ↔ etc.)
  • resonance → semantic weight from emotion + goal alignment
Exports atoms to data/analysis/language_atoms.json
"""

import json
import math
import random
import logging
import time
from pathlib import Path

from backend.modules.aion_language.meaning_field_engine import MFG
from backend.modules.aion_knowledge import knowledge_graph_core as akg

logger = logging.getLogger(__name__)

LANGUAGE_ATOM_PATH = Path("data/analysis/language_atoms.json")


# ─────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────
def synthesize_lexeme(concept_name: str) -> str:
    """
    Generate a pseudo-lexeme based on the concept’s symbolic root.
    Example: concept:resonant_equilibrium → 'resona' or 'equila'
    """
    base = concept_name.replace("concept:", "").replace("_", "")
    vowels = "aeiouy"
    start = "".join([ch for ch in base[:6] if ch.isalpha()])
    if not start:
        start = "lex"
    # simple phonemic shaping
    out = ""
    for ch in start:
        out += ch
        if random.random() < 0.25:
            out += random.choice(vowels)
    return out[:8]


def derive_resonance(c):
    """Combine mean_strength, emotion_bias, and goal_alignment into resonance metric."""
    s = c.get("mean_strength", 1.0)
    e = c.get("emotion_bias", 0.5)
    g = c.get("goal_alignment", 0.0)
    # Nonlinear fusion
    resonance = round((s * (0.6 + 0.4 * e)) * (1.0 + 0.5 * g), 3)
    return min(1.0, resonance)


# ─────────────────────────────────────────────
# Core Builder
# ─────────────────────────────────────────────
class LanguageAtomBuilder:
    def __init__(self):
        self.atoms = []

    def build_atoms(self):
        """Generate language atoms from meaning field clusters."""
        field = MFG.build_field()
        clusters = field.get("clusters", []) if field else []
        if not clusters:
            logger.warning("[LAB] No clusters found — run MFG first.")
            return []

        atoms = []
        for c in clusters:
            center = c["center"]
            lexeme = synthesize_lexeme(center)
            resonance = derive_resonance(c)

            # gather glyphs if any are linked to the concept
            glyphs = [
                s.replace("symbol:", "")
                for (s, p, o) in akg.triplets.keys()
                if o == center and s.startswith("symbol:")
            ] if hasattr(akg, "triplets") else []

            atom = {
                "center": center,
                "lexeme": lexeme,
                "glyphs": glyphs,
                "neighbors": c.get("neighbors", []),
                "resonance": resonance,
                "emotion_bias": c.get("emotion_bias", 0.5),
                "goal_alignment": c.get("goal_alignment", 0.0),
                "timestamp": time.time(),
            }
            atoms.append(atom)

        # Persist atoms
        LANGUAGE_ATOM_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LANGUAGE_ATOM_PATH, "w") as f:
            json.dump({"timestamp": time.time(), "atoms": atoms}, f, indent=2)

        self.atoms = atoms
        logger.info(f"[LAB] Built {len(atoms)} language atoms.")
        return atoms


# ─────────────────────────────────────────────
# Global Instance
# ─────────────────────────────────────────────
try:
    LAB
except NameError:
    try:
        LAB = LanguageAtomBuilder()
        print("🔤 LanguageAtomBuilder global instance initialized as LAB")
    except Exception as e:
        print(f"⚠️ Could not initialize LAB: {e}")
        LAB = None