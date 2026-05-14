"""
LanguageAtomBuilder - Phase 37B -> 39A : Language Atom Genesis & Reconstruction
---------------------------------------------------------------------------
Transforms meaning clusters (from MFG) into Language Atoms:
  * center -> concept anchor
  * lexeme -> synthetic linguistic handle
  * glyphs -> symbolic associations (Φ ⊕ ↔ etc.)
  * resonance -> semantic weight from emotion + goal alignment

Phase 39A extension:
  Adds `rebuild_from_photons()` to reconstruct atoms from imported photon fields
  for bidirectional photonic-semantic coupling.

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
    Generate a pseudo-lexeme based on the concept's symbolic root.
    Example: concept:resonant_equilibrium -> 'resona' or 'equila'
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
    resonance = round((s * (0.6 + 0.4 * e)) * (1.0 + 0.5 * g), 3)
    return min(1.0, resonance)


# ─────────────────────────────────────────────
# Core Builder
# ─────────────────────────────────────────────
class LanguageAtomBuilder:
    def __init__(self):
        self.atoms = []

    # ─────────────────────────────────────────────
    def build_atoms(self):
        """Generate language atoms from meaning field clusters."""
        field = MFG.build_field()
        clusters = field.get("clusters", []) if field else []
        if not clusters:
            logger.warning("[LAB] No clusters found - run MFG first.")
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
    def reinforce_AKG_from_atoms(self, weight: float = 0.1):
        """
        Phase 39A - Post-import reinforcement loop.
        Strengthens AKG semantic connections based on newly reconstructed atoms.
        Each atom increases the link strength between its center concept and related neighbors.

        Args:
            weight: Base reinforcement increment for each atom relation.
        """
        if not self.atoms:
            logger.warning("[LAB] No atoms to reinforce from.")
            return 0

        reinforced = 0
        for atom in self.atoms:
            c = atom["center"]
            resonance = atom.get("resonance", 0.8)
            emotion = atom.get("emotion_bias", 0.5)
            goal = atom.get("goal_alignment", 0.0)
            intensity = round(weight * (0.5 + resonance + emotion + goal) / 2, 3)

            # strengthen self resonance
            akg.add_triplet(c, "resonance_strength", str(intensity))

            # reinforce neighbor links if available
            for n in atom.get("neighbors", []):
                akg.add_triplet(c, "linked_to", n)
                akg.add_triplet(n, "linked_to", c)

            reinforced += 1

        logger.info(f"[LAB->AKG] Reinforced {reinforced} concepts from photon-derived atoms.")
        return reinforced

    # ─────────────────────────────────────────
    def create_atom(self, lexeme: str, definition: str | None = None):
        """
        Phase 41A.2 - Lexical Atom Constructor
        Creates a new Language Atom from a lexeme and optional definition.
        Returns a dict reference usable by MFG and AKG.
        """
        atom = {
            "id": f"atom:{lexeme}",
            "lexeme": lexeme,
            "definition": definition or "",
            "glyphs": [],
            "neighbors": [],
            "resonance": 0.8,
            "emotion_bias": 0.5,
            "goal_alignment": 0.0,
            "timestamp": __import__('time').time(),
        }
        # Append to internal atom list if not already present
        if not any(a["lexeme"] == lexeme for a in getattr(self, "atoms", [])):
            self.atoms.append(atom)
        return atom

    # ─────────────────────────────────────────────
    def rebuild_from_photons(self, photons: list):
        """
        Phase 39A - Reconstruct language atoms from imported photon field data.
        Used when re-importing .qphoto resonance fields into symbolic form.
        """
        self.atoms = []
        for p in photons:
            self.atoms.append({
                "center": f"concept:{p.get('λ', 'unknown')}",
                "lexeme": p.get("λ", "lexeme")[:6],
                "glyphs": [],
                "neighbors": [],
                "resonance": 0.8,
                "emotion_bias": float(p.get("π", 0.5)),
                "goal_alignment": float(p.get("μ", 0.0)),
                "timestamp": time.time(),
            })

        LANGUAGE_ATOM_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LANGUAGE_ATOM_PATH, "w") as f:
            json.dump({"timestamp": time.time(), "atoms": self.atoms}, f, indent=2)

        logger.info(f"[LAB] Rebuilt {len(self.atoms)} language atoms from photon data.")
        return self.atoms


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