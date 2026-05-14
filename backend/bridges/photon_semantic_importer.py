"""
Photon ↔ Semantic Importer - Phase 39A-39D
-------------------------------------------
Reads .qphoto resonance fields exported by Aion's photonic layer
and reconstructs semantic clusters and Language Atoms back into
the Aion Knowledge Graph (AKG).

Phase 39B adds persistence coupling via the ResonantMemoryCache (RMC),
which records photon resonance frequency and coherence over time and
applies long-term reinforcement to AKG concepts.

Phase 39C integrates the ResonantDriftMonitor (RDM),
allowing automatic detection of coherence decay and spawning
stabilization goals when semantic drift exceeds thresholds.

Phase 39D extends analysis through the TemporalHarmonicsMonitor (THM),
which predicts future drift by analyzing resonance oscillations and
creates anticipatory stabilization goals before coherence loss occurs.
"""

import json, logging, time
from pathlib import Path
from backend.modules.aion_knowledge import knowledge_graph_core as akg
from backend.modules.aion_language.meaning_field_engine import MFG
from backend.modules.aion_language.language_atom_builder import LAB
from backend.modules.aion_language.resonant_memory_cache import RMC    # 🧠 Phase 39B
from backend.modules.aion_language.resonant_drift_monitor import RDM   # 🌊 Phase 39C
from backend.modules.aion_language.temporal_harmonics_monitor import THM  # 🕓 Phase 39D

logger = logging.getLogger(__name__)


class PhotonSemanticImporter:
    def __init__(self, photon_dir="data/photon_records"):
        self.photon_dir = Path(photon_dir)

    def import_field(self, filename: str):
        """
        Phase 39A -> 39D - Photon -> Symbolic Import + Resonant Memory + Drift + Predictive Harmonics
        Loads a .qphoto resonance field, reconstructs photons, clusters, and atoms,
        updates long-term resonance memory (RMC), analyzes drift (RDM),
        and performs harmonic forecasting (THM).
        """
        path = Path(f"data/photon_records/{filename}")
        if not path.exists():
            logger.error(f"[Importer] File not found: {path}")
            return None

        # ✅ Load the raw photon data
        with open(path) as f:
            data = json.load(f)

        photons = data.get("photons", [])
        logger.info(f"[Importer] Loaded {len(photons)} photon entries from {filename}")

        # 1️⃣ Rebuild concepts in AKG
        for p in photons:
            cid = f"concept:{p.get('λ', 'unknown')}"
            akg.add_triplet(cid, "phase", str(p.get("φ", 0.0)))
            akg.add_triplet(cid, "projection", str(p.get("π", 0.0)))

        # 2️⃣ Rebuild meaning field clusters
        clusters = []
        for p in photons:
            clusters.append({
                "center": f"concept:{p.get('λ', 'unknown')}",
                "neighbors": [],
                "emotion_bias": float(p.get("π", 0.5)),
                "goal_alignment": float(p.get("μ", 0.0)),
                "link_count": 1,
                "mean_strength": 1.0
            })
        MFG.field = {"timestamp": time.time(), "clusters": clusters}

        # 3️⃣ Rebuild language atoms
        atoms = []
        for c in clusters:
            atoms.append({
                "center": c["center"],
                "lexeme": c["center"].split(":")[-1][:6],
                "glyphs": [],
                "neighbors": [],
                "resonance": 0.8,
                "emotion_bias": c["emotion_bias"],
                "goal_alignment": c["goal_alignment"],
                "timestamp": time.time(),
            })
        LAB.atoms = atoms
        logger.info(f"[Importer] Reconstructed {len(atoms)} language atoms from photon field.")

        # 4️⃣ Persist resonance memory + reinforcement
        if photons:
            RMC.update_from_photons(photons)
            RMC.reinforce_AKG(weight=0.3)

        # 5️⃣ Analyze temporal drift in coherence
        RDM.analyze_drift()

        # 6️⃣ Predict harmonic oscillations for proactive stabilization
        THM.analyze_harmonics()

        # ✅ Unified return structure including photons
        return {
            "photons": photons,
            "clusters": clusters,
            "atoms": atoms
        }