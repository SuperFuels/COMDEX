# 📁 codex_context_adapter.py
# Bridges CodexCore to DreamCore, Tessaris, and GlyphOS subsystems

import time
from backend.modules.codex.codex_fabric import CodexFabric
from backend.modules.dimensions.dimension_engine import get_current_container_metadata
from backend.modules.aion.dream_core import get_last_dream_summary
from backend.modules.tessaris.tessaris_engine import get_active_thought_context

# Initialize CodexFabric globally (can also be passed in)
codex_fabric = CodexFabric()

def adapt_codex_context(glyph, source):
    """
    Builds symbolic execution context from glyph + source system.
    Includes source type, time, container info, dream context, and tessaris logic thread.
    """
    context = {
        "source": source,
        "timestamp": time.time(),
        "tags": [],
        "container": {},
        "dream": {},
        "tessaris": {}
    }

    # Symbolic tags from source system
    if "dream" in source:
        context["tags"].append("dream-reflection")
        context["dream"] = get_last_dream_summary()
    elif "tessaris" in source:
        context["tags"].append("symbolic-thought")
        context["tessaris"] = get_active_thought_context()
    elif "memory" in source:
        context["tags"].append("memory-loop")

    # Include container metadata (time, avatar state, physics mode, etc.)
    try:
        context["container"] = get_current_container_metadata()
    except Exception as e:
        context["container"] = {"error": str(e)}

    return context

def route_glyph_to_codex(glyph, context):
    """
    Send glyph + enriched context into CodexFabric for execution.
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