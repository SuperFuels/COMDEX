"""
ResonantInterpreter - Phase 38A : Language ↔ Photon Resonance Field
-------------------------------------------------------------------
Translates Language Atoms into photonic QWave events and builds a
contextual resonance field Ψ that allows Aion to *understand* and
*emit* meaning as coherent waveforms.

Inputs  : LAB.atoms (language-semantic units)
Outputs : data/analysis/resonant_fields.json (aggregate resonance field)
"""

import json, math, time, logging
from pathlib import Path
from statistics import mean
from random import uniform

logger = logging.getLogger(__name__)

# Optional back-imports
try:
    from backend.modules.aion_language.language_atom_builder import LAB
except Exception:
    LAB = None
try:
    from backend.bridges.photon_AKG_bridge import PhotonAKGBridge
except Exception:
    PhotonAKGBridge = None

RESONANT_FIELD_PATH = Path("data/analysis/resonant_fields.json")

class ResonantInterpreter:
    """Phase 38A - Constructs and evaluates semantic resonance fields."""

    def __init__(self):
        self.last_field = None
        self.bridge = PhotonAKGBridge() if PhotonAKGBridge else None

    # ─────────────────────────────────────────
    def interpret_atoms(self, atoms=None, export_name: str | None = None):
        """
        Interpret a set of language atoms into a resonance field and
        optionally export it under a custom .qphoto name.

        Args:
            atoms: List of atoms (defaults to LAB.atoms if None)
            export_name: Optional filename for the exported resonance field
        """
        from backend.bridges.photon_AKG_bridge import PhotonAKGBridge
        bridge = PhotonAKGBridge()

        if atoms is None:
            try:
                from backend.modules.aion_language.language_atom_builder import LAB
                atoms = LAB.atoms
            except Exception:
                logger.warning("[ResInt] No atoms provided and LAB unavailable.")
                return None

        if not atoms:
            logger.warning("[ResInt] No language atoms available.")
            return None

        # Compute coherence as normalized connectivity
        coherence = min(1.0, len(atoms) / 10)
        field = {
            "timestamp": time.time(),
            "semantic_coherence": coherence,
            "atom_count": len(atoms),
            "atoms": atoms,
        }

        # Export resonance field
        fname = export_name or f"resonance_field_{int(field['timestamp'])}.qphoto"
        try:
            bridge.export_resonance_field(field, filename=fname)
            logger.info(f"[ResInt] Exported resonance field -> data/photon_records/{fname}")
        except Exception as e:
            logger.warning(f"[ResInt->Photon] Export failed: {e}")

        return field

    # ─────────────────────────────────────────
    def compare_with_intent(self, intent_field):
        """
        Compare current resonance field with an intent field to
        compute semantic overlap (cosine-style coherence).
        """
        if not self.last_field or not intent_field:
            return 0.0

        A = [q["amplitude"] for q in self.last_field["qwaves"]]
        B = [q["amplitude"] for q in intent_field.get("qwaves", [])[:len(A)]]
        if not A or not B:
            return 0.0

        dot = sum(a*b for a, b in zip(A, B))
        norm = math.sqrt(sum(a*a for a in A) * sum(b*b for b in B))
        return round(dot / norm, 3) if norm else 0.0


# ─────────────────────────────────────────────
# Global Instance
# ─────────────────────────────────────────────
try:
    RI
except NameError:
    try:
        RI = ResonantInterpreter()
        print("💫 ResonantInterpreter global instance initialized as RI")
    except Exception as e:
        print(f"⚠️ Could not initialize RI: {e}")
        RI = None