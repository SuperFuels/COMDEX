# knowledge_graph_adapter.py

import time
import logging
from typing import Dict, Optional

from backend.modules.knowledge_graph.knowledge_graph_writer import (
    register_entity,
    link_source,
    attach_provenance,
)

logger = logging.getLogger(__name__)

def store_wave_measurement_in_kg(measurement: Dict, source_wave: Optional[Dict] = None):
    """
    Store a measured wave result into the Knowledge Graph.

    Args:
        measurement: Dictionary from `measure_wave(...)` output
        source_wave: Optional full WaveState.to_dict() if available
    """
    try:
        glyph_id = measurement.get("glyph_id", "unknown")
        timestamp = measurement.get("timestamp", time.time())
        amplitude = measurement.get("amplitude", 0.0)
        coherence = measurement.get("coherence", 0.0)
        policy = measurement.get("policy", "unspecified")

        node_id = f"WAVE_MEASURE_{glyph_id}_{int(timestamp * 1000)}"

        # Register the node
        register_entity({
            "id": node_id,
            "type": "WaveMeasurement",
            "label": f"Measurement of {glyph_id}",
            "properties": {
                "glyph_id": glyph_id,
                "amplitude": amplitude,
                "coherence": coherence,
                "policy": policy,
                "timestamp": timestamp,
            }
        })

        # Link to glyph source
        link_source(node_id, glyph_id, relation="measuredFrom")

        # Link provenance if available
        if source_wave:
            container_id = source_wave.get("metadata", {}).get("container_id")
            if container_id:
                attach_provenance(node_id, container_id, relation="observedIn")

        logger.info(f"[KG] ✅ Stored wave measurement for glyph: {glyph_id}")

        return node_id

    except Exception as e:
        logger.warning(f"[KG] ⚠️ Failed to store wave measurement: {e}")
        return None