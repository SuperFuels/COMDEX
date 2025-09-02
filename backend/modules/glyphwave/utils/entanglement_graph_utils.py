# backend/modules/glyphwave/utils/entanglement_graph_utils.py

from backend.modules.glyphwave.core.entangled_wave import EntangledWave

def attach_entangled_graph_to_container(container: dict, entangled_wave: EntangledWave):
    """
    Injects the entanglement graph (nodes + links) into the container["trace"].
    """
    container.setdefault("trace", {})
    container["trace"]["entanglementGraph"] = entangled_wave.to_graph()