from typing import Dict, Any
import logging

from backend.modules.symbolic.symbol_tree_generator import build_symbolic_tree_from_container
from backend.modules.knowledge_graph.knowledge_graph_writer import store_container_metadata
from backend.modules.runtime.container_path_utils import container_id_to_path

def inject_hst_to_container(container: Dict[str, Any], context: Dict[str, Any] = {}) -> Dict[str, Any]:
    """
    Builds and injects the SymbolicMeaningTree into a given `.dc` container.
    Injects into container['hst']['symbolicTree'], and optionally logs metadata to the Knowledge Graph.
    
    Parameters:
        container (Dict): The symbolic container (e.g., .dc.json) as a dictionary.
        context (Dict): Optional metadata:
            - container_id: used to auto-resolve container_path if not provided
            - container_path: for Knowledge Graph injection
            - coord: location or context of the operation
            - source: source of injection (e.g., "prediction_engine", "creative_core", etc.)

    Returns:
        The updated container dictionary with 'hst' field added.
    """
    try:
        tree = build_symbolic_tree_from_container(container)
        container.setdefault("hst", {})["symbolicTree"] = tree.to_dict()

        # ✅ Determine container path
        container_path = context.get("container_path")
        if not container_path and "container_id" in context:
            container_path = container_id_to_path(context["container_id"])

        store_container_metadata(
            container_path=container_path or "unknown",
            coord=context.get("coord", "0:0"),
            metadata={
                "symbolic_tree_injected": True,
                "symbol_count": len(tree.node_index),
                "root_label": getattr(tree.root.glyph, "label", "none") if tree.root else "none",
                "source": context.get("source", "hst_injector")
            }
        )

        return container

    except Exception as e:
        logging.warning(f"[HST Injection] Failed to inject SymbolicMeaningTree: {e}")
        return container