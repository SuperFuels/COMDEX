import hashlib
import time
from typing import Optional, List, Dict
from backend.modules.glyphwave.core.wave_state import get_active_wave_state_by_container_id

def generate_qwave_id(glyph_id: str, state: str = "", tick: int = None) -> str:
    base = f"{glyph_id}:{state}:{tick or int(time.time() * 1000)}"
    return hashlib.sha256(base.encode()).hexdigest()[:16]

def collect_qwave_beams(container_id: str) -> List[Dict]:
    """
    Collect live QWave beams from the WaveState runtime for the given container ID.
    Returns a list of beam dictionaries, suitable for export.
    """
    wave_state = get_active_wave_state_by_container_id(container_id)
    if not wave_state:
        return []

    beam_list = []
    for beam in wave_state.get("entangled_beams", []):
        beam_list.append({
            "id": beam.get("id"),
            "source": beam.get("source_id"),
            "target": beam.get("target_id"),
            "carrier_type": beam.get("carrier_type", "SIMULATED"),
            "modulation": beam.get("modulation_strategy", "SimPhase"),
            "coherence": beam.get("coherence_score", 1.0),
            "entangled_path": beam.get("entangled_path", []),
            "mutation_trace": beam.get("mutation_trace", []),
            "collapse_state": beam.get("collapse_state", "original"),
            "metadata": beam.get("metadata", {}),
        })

    return beam_list

def export_qwave_beams(container: dict, beam_store: list, context: Optional[dict] = None):
    qwave_export = []
    for beam in beam_store:
        qwave_export.append({
            "beam_id": beam.get("id"),
            "source_id": beam.get("source"),
            "target_id": beam.get("target"),
            "carrier_type": beam.get("carrier_type", "SIMULATED"),
            "modulation_strategy": beam.get("modulation", "SimPhase"),
            "coherence": beam.get("coherence", 1.0),
            "entangled_path": beam.get("entangled_path", []),
            "mutation_trace": beam.get("mutation_trace", []),
            "collapse_state": beam.get("collapse_state", "original"),
            "metadata": beam.get("metadata", {}),
        })

    container["qwave_beams"] = qwave_export
    if context:
        container["multiverse_frame"] = context.get("frame", "original")

__all__ = ["collect_qwave_beams", "export_qwave_beams", "generate_qwave_id"]