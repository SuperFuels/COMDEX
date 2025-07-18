# 📁 codex_context_adapter.py
# Bridges CodexCore to DreamCore, Tessaris, and GlyphOS subsystems
import time
from backend.modules.codex.codex_fabric import CodexFabric

# Initialize the CodexFabric globally (or could be passed into this adapter later)
codex_fabric = CodexFabric()

def adapt_codex_context(glyph, source):
    """
    Builds symbolic execution context from glyph + source system.
    """
    context = {
        "source": source,
        "timestamp": time.time(),
        "tags": []
    }
    if "dream" in source:
        context["tags"].append("dream-reflection")
    elif "tessaris" in source:
        context["tags"].append("symbolic-thought")
    elif "memory" in source:
        context["tags"].append("memory-loop")

    return context

def route_glyph_to_codex(glyph, context):
    """
    Send glyph + context into CodexFabric for execution.
    Returns execution result from the appropriate CodexCore node.
    """
    return codex_fabric.execute_glyph(glyph, context)

def register_codex_node(container_id, codex_core_instance):
    """
    Add a new CodexCore (from a .dc container) into the CodexFabric runtime grid.
    """
    codex_fabric.register_node(container_id, codex_core_instance)

def tick_codex_fabric():
    """
    Trigger one execution tick across all active CodexCore nodes.
    """
    codex_fabric.tick_all()