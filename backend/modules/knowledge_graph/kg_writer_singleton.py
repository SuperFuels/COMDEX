import importlib
import traceback
import logging
from typing import Any, Callable, Optional

# 🧠 Singleton holder for the KnowledgeGraphWriter instance
_kg_writer_instance: Optional[Any] = None
_KG_WRITER_CLASS: Optional[Callable[[], Any]] = None  # Lazy-loaded class reference
_build_tree_from_container = None  # Lazy-imported symbolic tree builder
_export_tree_to_kg = None  # Lazy-imported KG writer method

def get_kg_writer() -> Any:
    """
    Lazily initializes and returns the singleton KnowledgeGraphWriter instance.
    This avoids circular import issues by delaying class resolution until needed.
    """
    global _kg_writer_instance, _KG_WRITER_CLASS

    if _kg_writer_instance is not None:
        return _kg_writer_instance

    try:
        if _KG_WRITER_CLASS is None:
            # 🔁 Lazy import to avoid circular import loop
            module = importlib.import_module("backend.modules.knowledge_graph.knowledge_graph_writer")

            if not hasattr(module, "KnowledgeGraphWriter"):
                raise ImportError(
                    "[kg_writer_singleton] ❌ 'KnowledgeGraphWriter' class not found in module."
                )

            _KG_WRITER_CLASS = getattr(module, "KnowledgeGraphWriter")

        _kg_writer_instance = _KG_WRITER_CLASS()
        return _kg_writer_instance

    except Exception as e:
        trace = "".join(traceback.format_stack(limit=10))
        raise RuntimeError(
            f"[kg_writer_singleton] ❌ Failed to initialize KnowledgeGraphWriter: {e}\n"
            f"[kg_writer_singleton] 📍 Stack Trace:\n{trace}"
        )

def get_strategy_planner_kg_writer() -> Any:
    """
    🔁 Alias for get_kg_writer(), used in StrategyPlanner and other contexts to clarify purpose.
    """
    return get_kg_writer()

def write_glyph_event(event_type: str, event: dict, container_id: Optional[str] = None) -> None:
    """
    Proxy passthrough to standalone write_glyph_event() in knowledge_graph_writer module.
    """
    try:
        module = importlib.import_module("backend.modules.knowledge_graph.knowledge_graph_writer")

        real_writer = getattr(module, "write_glyph_event", None)
        if real_writer is None:
            raise ImportError("write_glyph_event function not found in knowledge_graph_writer module.")

        return real_writer(event_type=event_type, event=event, container_id=container_id)

    except Exception as e:
        trace = "".join(traceback.format_stack(limit=10))
        raise RuntimeError(
            f"[kg_writer_singleton] ❌ Failed to call write_glyph_event: {e}\n"
            f"[kg_writer_singleton] 📍 Stack Trace:\n{trace}"
        )

def get_glyph_trace_for_container(container_id: str) -> dict:
    """
    Proxy passthrough to get_glyph_trace_for_container() in knowledge_graph_writer module.
    Used by HolographicSymbolTree and related systems.
    """
    try:
        module = importlib.import_module("backend.modules.knowledge_graph.knowledge_graph_writer")

        real_func = getattr(module, "get_glyph_trace_for_container", None)
        if real_func is None:
            raise ImportError("get_glyph_trace_for_container not found in knowledge_graph_writer module.")

        return real_func(container_id)

    except Exception as e:
        trace = "".join(traceback.format_stack(limit=10))
        raise RuntimeError(
            f"[kg_writer_singleton] ❌ Failed to call get_glyph_trace_for_container: {e}\n"
            f"[kg_writer_singleton] 📍 Stack Trace:\n{trace}"
        )

def export_symbol_tree_if_enabled(container_id: str) -> None:
    """
    🌳 Lazy-proxy to build and export the symbolic meaning tree.
    This avoids import loops by loading build_tree_from_container only when called.
    """
    global _build_tree_from_container, _export_tree_to_kg
    try:
        if _build_tree_from_container is None:
            from backend.modules.symbolic.symbol_tree_generator import build_tree_from_container
            _build_tree_from_container = build_tree_from_container

        if _export_tree_to_kg is None:
            from backend.modules.knowledge_graph.knowledge_graph_writer import export_tree_to_kg
            _export_tree_to_kg = export_tree_to_kg

        tree = _build_tree_from_container(container_id)
        _export_tree_to_kg(tree)

        print(f"[🌳] Symbolic Tree auto-exported for container: {container_id}")

    except Exception as e:
        logging.warning(f"[kg_writer_singleton] ⚠️ Failed to export symbolic tree for {container_id}: {e}")

def get_crdt_registry() -> Optional[Any]:
    """
    Returns the CRDT registry from the KnowledgeGraphWriter instance.
    """
    try:
        writer = get_kg_writer()
        return getattr(writer, "crdt_registry", None)
    except Exception as e:
        logging.warning(f"[kg_writer_singleton] ⚠️ Could not access crdt_registry: {e}")
        return None

__all__ = [
    "get_kg_writer",
    "get_strategy_planner_kg_writer",
    "write_glyph_event",
    "get_glyph_trace_for_container",
    "get_crdt_registry",
    "export_symbol_tree_if_enabled"
]