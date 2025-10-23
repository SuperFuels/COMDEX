"""
Photon ↔ AKG Bridge — Phase 36A
--------------------------------
Maps Aion Knowledge Graph (AKG) concepts to Photon Language waveforms
and serializes them for QQC resonance transmission.

Each concept is represented as a photonic signature:
Φ = (λ, φ, μ, π, ⊕, ↔)
   wavelength | phase | measurement | projection | superposition | entanglement
Serialized as .qphoto and stored under data/photon_records/.

Author: Tessaris Research Group
Date: Phase 36A (October 2025)
"""

import json, time
from pathlib import Path
from dataclasses import dataclass, asdict


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


class PhotonAKGBridge:
    """
    Converts AKG concept metadata into Photon Language resonance vectors.
    Designed for bidirectional coupling with the Quantum Quad Core (QQC).
    """

    def __init__(self, output_dir="data/photon_records"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────────────────────
    def encode_concept(self, concept_name: str) -> PhotonRecord:
        """
        Generate deterministic pseudo-photonic parameters from the concept name.
        Later phases will replace this heuristic with true resonance data.
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

    # ─────────────────────────────────────────────────────────────
    def serialize(self, record: PhotonRecord) -> Path:
        """Write .qphoto JSON file to the photon record directory."""
        file_path = self.output_dir / f"{record.concept_id}.qphoto"
        with open(file_path, "w") as fp:
            json.dump(asdict(record), fp, indent=2)
        return file_path

    # ─────────────────────────────────────────────────────────────
    def export_concept(self, concept_name: str) -> PhotonRecord:
        """
        Public API: encodes, serializes, and logs a concept’s photon record.
        Called automatically by AKG concept-creation hooks.
        """
        rec = self.encode_concept(concept_name)
        fpath = self.serialize(rec)
        print(f"✨ Photon record exported → {fpath}")
        return rec