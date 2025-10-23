"""
Photon ↔ AKG Bridge — Phase 36A – 38B
--------------------------------------
Maps Aion Knowledge Graph (AKG) concepts to Photon Language waveforms
and serializes them for QQC resonance transmission.

Each concept is represented as a photonic signature:
Φ = (λ, φ, μ, π, ⊕, ↔)
   wavelength | phase | measurement | projection | superposition | entanglement

Phase 38 adds resonance-field export for the Aion Language subsystem,
allowing full semantic fields (Ψ) to be written as .qphoto records.

Author: Tessaris Research Group
Date: Phase 36A – 38B (October 2025)
"""

import json, time
from pathlib import Path
from dataclasses import dataclass, asdict


# ─────────────────────────────────────────────
# Data Model
# ─────────────────────────────────────────────
@dataclass
class PhotonRecord:
    """Encapsulates a photonic resonance signature for one AKG concept."""
    concept_id: str
    wavelength: float
    phase: float
    measurement: float
    projection: float
    superposition: float
    entanglement: float
    timestamp: float = time.time()


# ─────────────────────────────────────────────
# Bridge Implementation
# ─────────────────────────────────────────────
class PhotonAKGBridge:
    """
    Converts AKG concept metadata into Photon Language resonance vectors
    and manages serialization for QQC resonance transport.
    """

    def __init__(self, output_dir: str = "data/photon_records"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────
    # Phase 36A — Concept Encoding
    # ─────────────────────────────────────────
    def encode_concept(self, concept_name: str) -> PhotonRecord:
        """
        Generate deterministic pseudo-photonic parameters from the concept name.
        Later phases replace this heuristic with true resonance data.
        """
        h = abs(hash(concept_name)) % 100000
        return PhotonRecord(
            concept_id=concept_name,
            wavelength=(h % 997) / 997.0,
            phase=((h // 7) % 360) / 360.0,
            measurement=0.5,
            projection=0.5,
            superposition=0.7,
            entanglement=0.6,
        )

    # ─────────────────────────────────────────
    def serialize(self, record: PhotonRecord) -> Path:
        """Write a .qphoto JSON file for a single photon record."""
        file_path = self.output_dir / f"{record.concept_id}.qphoto"
        with open(file_path, "w") as fp:
            json.dump(asdict(record), fp, indent=2)
        return file_path

    # ─────────────────────────────────────────
    def export_concept(self, concept_name: str) -> PhotonRecord:
        """
        Public API — Encodes and serializes a concept’s photon record.
        Called automatically by AKG concept-creation hooks.
        """
        rec = self.encode_concept(concept_name)
        fpath = self.serialize(rec)
        print(f"✨ Photon record exported → {fpath}")
        return rec

    # ─────────────────────────────────────────
    # Phase 38 Support — Resonance Field Export
    # ─────────────────────────────────────────
    def export_resonance_field(self, field: dict, filename: str | None = None):
        """
        Phase 38B–39A — Export semantic resonance field into Photon Language form.
        Converts semantic atoms or clusters into photonic signatures (Φ).
        """
        import json, time
        from pathlib import Path

        base_dir = Path("data/photon_records")
        base_dir.mkdir(parents=True, exist_ok=True)
        fname = filename or f"resonance_field_{int(time.time())}.qphoto"
        fpath = base_dir / fname

        # Support both clusters or atoms as source
        sources = field.get("atoms") or field.get("clusters") or []
        photons = []
        for s in sources:
            photons.append({
                "λ": s.get("center", "unknown"),             # semantic wavelength
                "φ": s.get("emotion_bias", 0.5),             # phase alignment
                "μ": s.get("goal_alignment", 0.0),           # measurement coupling
                "π": s.get("emotion_bias", 0.5),             # projection/emotion
                "⊕": s.get("resonance", 0.8),                # superposition
                "↔": s.get("center", "unknown"),              # entanglement id
            })

        photon_field = {
            "timestamp": field.get("timestamp", time.time()),
            "semantic_coherence": field.get("semantic_coherence", 1.0),
            "photons": photons
        }

        with open(fpath, "w") as f:
            json.dump(photon_field, f, indent=2)

        print(f"✨ Photon resonance field exported → {fpath}")
        return fpath