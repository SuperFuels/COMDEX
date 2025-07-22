# 📁 codex_context_adapter.py
# Bridges CodexCore to DreamCore, Tessaris, and GlyphOS subsystems

import time
from backend.modules.codex.codex_fabric import CodexFabric
from backend.modules.dimensions.dimension_engine import get_current_container_metadata
from backend.modules.aion.dream_core import get_last_dream_summary
from backend.modules.tessaris.tessaris_engine import get_active_thought_context
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# ✅ Register for symbolic upgrades
DNA_SWITCH.register(__file__)

# Global instance
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

    # Symbolic tagging
    source_lower = source.lower()
    if "dream" in source_lower:
        context["tags"].append("dream-reflection")
        try:
            context["dream"] = get_last_dream_summary()
        except:
            context["dream"] = {"error": "no_dream_data"}
    if "tessaris" in source_lower:
        context["tags"].append("symbolic-thought")
        try:
            context["tessaris"] = get_active_thought_context()
        except:
            context["tessaris"] = {"error": "no_thought_data"}
    if "memory" in source_lower:
        context["tags"].append("memory-loop")
    if "mutation" in source_lower:
        context["tags"].append("mutation-sequence")
    if "boot" in source_lower:
        context["tags"].append("boot-trigger")

    # Container metadata
    try:
        context["container"] = get_current_container_metadata()
    except Exception as e:
        context["container"] = {"error": str(e)}

    return context

def route_glyph_to_codex(glyph, context):
    """
    Send glyph + enriched context into CodexFabric for execution.
    Returns execution payload (status, cost, trace, etc.)
    """
    try:
        return codex_fabric.execute_glyph(glyph, context)
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "glyph": glyph,
            "context": context
        }

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