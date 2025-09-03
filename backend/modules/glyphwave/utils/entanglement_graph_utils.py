# backend/modules/glyphwave/utils/entanglement_graph_utils.py

from backend.modules.glyphwave.core.entangled_wave import EntangledWave

def attach_entangled_graph_to_container(container: dict, entangled_wave: EntangledWave):
    """
    Injects the entanglement graph (nodes + links) into the container["trace"], with spoof prevention.
    """
    graph = entangled_wave.to_graph()

    # 🔒 Spoof protection: Ensure all entangled links reference valid node IDs
    node_ids = {node.get("id") for node in graph.get("nodes", [])}
    for link in graph.get("links", []):
        src = link.get("source")
        tgt = link.get("target")
        if src not in node_ids or tgt not in node_ids:
            raise ValueError(f"🚫 Spoofed entanglement link detected: {src} → {tgt}")

    # ✅ Safe to inject entanglement graph
    container.setdefault("trace", {})
    container["trace"]["entanglementGraph"] = graph