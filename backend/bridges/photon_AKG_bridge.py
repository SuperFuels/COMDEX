"""
Photon ↔ AKG Bridge — Phase 36A–40C
------------------------------------
Maps Aion Knowledge Graph (AKG) concepts to Photon Language waveforms
and serializes them for QQC resonance transmission.

Each concept is represented as a photonic signature:
Φ = (λ, φ, μ, π, ⊕, ↔)
   wavelength | phase | measurement | projection | superposition | entanglement

Phase 38B added resonance-field export for the Aion Language subsystem.
Phase 40C extends the bridge with harmonic emission capability,
allowing the Harmonic Stabilizer Engine (HSE) to send corrective packets
back through the resonance channel.

Author: Tessaris Research Group
Date: Phases 36A–40C (October 2025)
"""

import json, time, logging
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

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
    Converts AKG concept metadata into Photon Language resonance vectors,
    manages serialization for QQC resonance transport, and now accepts
    harmonic correction emissions from higher control layers.
    """

    def __init__(self, output_dir: str = "data/photon_records"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.emission_log = Path("data/feedback/photon_bridge_log.json")

    # ─────────────────────────────────────────
    # Phase 36A — Concept Encoding
    # ─────────────────────────────────────────
    def encode_concept(self, concept_name: str) -> PhotonRecord:
        """Generate deterministic pseudo-photonic parameters from a concept name."""
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
        fpath = self.output_dir / f"{record.concept_id}.qphoto"
        with open(fpath, "w") as fp:
            json.dump(asdict(record), fp, indent=2)
        logger.info(f"[PAB] Serialized photon record → {fpath}")
        return fpath

    # ─────────────────────────────────────────
    def export_concept(self, concept_name: str) -> PhotonRecord:
        """Public API — encodes and serializes a concept’s photon record."""
        rec = self.encode_concept(concept_name)
        fpath = self.serialize(rec)
        print(f"✨ Photon record exported → {fpath}")
        return rec

    # ─────────────────────────────────────────
    # Phase 38B–39A — Resonance Field Export
    # ─────────────────────────────────────────
    def export_resonance_field(self, field: dict, filename: str | None = None):
        """Export semantic resonance field into Photon Language form (.qphoto)."""
        base_dir = self.output_dir
        base_dir.mkdir(parents=True, exist_ok=True)
        fname = filename or f"resonance_field_{int(time.time())}.qphoto"
        fpath = base_dir / fname

        # Support both clusters or atoms as source
        sources = field.get("atoms") or field.get("clusters") or []
        photons = []
        for s in sources:
            photons.append({
                "λ": s.get("center", "unknown"),
                "φ": s.get("emotion_bias", 0.5),
                "μ": s.get("goal_alignment", 0.0),
                "π": s.get("emotion_bias", 0.5),
                "⊕": s.get("resonance", 0.8),
                "↔": s.get("center", "unknown"),
            })

        photon_field = {
            "timestamp": field.get("timestamp", time.time()),
            "semantic_coherence": field.get("semantic_coherence", 1.0),
            "photons": photons
        }

        with open(fpath, "w") as f:
            json.dump(photon_field, f, indent=2)

        logger.info(f"[PAB] Photon resonance field exported → {fpath}")
        return fpath

    # ─────────────────────────────────────────
    # Phase 40C — Harmonic Emission Interface
    # ─────────────────────────────────────────
    def emit(self, packet: dict):
        """
        Accepts a correction or photon-field packet and logs it for QQC relay.
        This provides a unified entry point for the HSE to transmit feedback.
        """
        packet["timestamp"] = packet.get("timestamp", time.time())
        msg = f"[PAB] Emitting {packet.get('type')} → {packet.get('target', 'unknown')}"
        logger.info(msg)
        print(msg)

        # append to persistent log
        self.emission_log.parent.mkdir(parents=True, exist_ok=True)
        if self.emission_log.exists():
            with open(self.emission_log) as f:
                data = json.load(f)
        else:
            data = {"packets": []}
        data["packets"].append(packet)
        with open(self.emission_log, "w") as f:
            json.dump(data, f, indent=2)
        return True


# ─────────────────────────────────────────────
try:
    PAB
except NameError:
    try:
        PAB = PhotonAKGBridge()
        print("🔗 PhotonAKGBridge global instance initialized as PAB")
    except Exception as e:
        print(f"⚠️ Could not initialize PAB: {e}")
        PAB = None