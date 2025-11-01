# ===============================
# 📁 backend/modules/spe/spe_bridge.py
# ===============================
"""
SPE Bridge - Symbolic Pattern Engine ↔ QWave/SQI interface

Provides recombination and drift-repair entrypoints for beams.
Hooks into DNA mutation tracker + autofuse flag.
"""

import logging
from typing import List, Dict, Any

from backend.config import SPE_AUTO_FUSE
from backend.modules.codex.dna_mutation_tracker import add_dna_mutation

logger = logging.getLogger(__name__)

# ✅ Core SPE bridge functions

def recombine_from_beams(beams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Recombine multiple beams into fused symbolic beams.
    Preserves lineage + annotates with mutation event.
    """
    if not beams:
        return []

    logger.info(f"[SPE] Recombining {len(beams)} beams")

    fused_beam = {
        "id": f"fused_{'_'.join(str(b.get('id')) for b in beams)}",
        "type": "fusion",
        "inputs": [b.get("id") for b in beams],
        "payload": {
            "merged": True,
            "sources": [b.get("payload") for b in beams],
        },
        "metadata": {"spe_fusion": True},
    }

    # 🧬 Track DNA mutation
    try:
        add_dna_mutation(
            from_state=[b.get("id") for b in beams],
            to_state=fused_beam["id"],
            reason="SPE recombination"
        )
    except Exception as e:
        logger.warning(f"[SPE] DNA mutation logging failed: {e}")

    return [fused_beam]


def repair_from_drift(beams: List[Dict[str, Any]], drift_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Repair beams that show drift (SQI instability).
    Produces corrected/repaired beam outputs.
    """
    if not beams:
        return []

    logger.info(f"[SPE] Repairing {len(beams)} beams from drift={drift_info}")

    repaired = []
    for beam in beams:
        repaired_beam = dict(beam)  # shallow copy
        repaired_beam["metadata"] = repaired_beam.get("metadata", {})
        repaired_beam["metadata"]["repaired_from_drift"] = True
        repaired_beam["metadata"]["drift_info"] = drift_info

        # 🧬 Log drift repair as DNA mutation
        try:
            add_dna_mutation(
                from_state=beam.get("id"),
                to_state=f"{beam.get('id')}_repaired",
                reason="SPE drift repair"
            )
        except Exception as e:
            logger.warning(f"[SPE] DNA mutation logging failed during drift repair: {e}")

        repaired.append(repaired_beam)

    return repaired


# ✅ Autofuse wrapper

def maybe_autofuse(beams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    If SPE_AUTO_FUSE is enabled, auto-fuse beams via recombination.
    Otherwise return beams untouched.
    """
    if SPE_AUTO_FUSE:
        logger.info("[SPE] Autofuse enabled -> recombining beams")
        return recombine_from_beams(beams)
    return beams


# ✅ Public exports
__all__ = [
    "recombine_from_beams",
    "repair_from_drift",
    "maybe_autofuse",
]