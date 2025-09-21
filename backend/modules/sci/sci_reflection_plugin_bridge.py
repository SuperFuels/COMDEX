# File: backend/modules/sci/sci_reflection_plugin_bridge.py

from typing import Dict, Any, Optional
from backend.core.plugins.plugin_manager import get_all_plugins
from backend.modules.codex.codex_scroll_injector import inject_scroll
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.sci.qfc_ws_broadcaster import broadcast_qfc_state


def inject_reflection_into_field(field_state: Dict[str, Any], observer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Passes the field state through all loaded reflection plugins.
    Allows plugins to inject symbolic scrolls, insight glyphs, or memory hooks.
    """
    for plugin in get_all_plugins():
        if hasattr(plugin, "reflect"):
            try:
                updated_state = plugin.reflect(field_state, observer_id=observer_id)
                if updated_state and isinstance(updated_state, dict):
                    field_state.update(updated_state)
                    print(f"[Reflection] {plugin.__class__.__name__} updated field_state.")
            except Exception as e:
                print(f"[Reflection] {plugin.__class__.__name__} failed: {e}")
    return field_state


async def write_reflection_to_memory_and_broadcast(field_state: Dict[str, Any], observer_id: Optional[str] = None):
    """
    Writes reflective scrolls to container memory + triggers WebSocket broadcast of the updated QFC state.
    """
    kg_writer = get_kg_writer()

    reflection_scroll = {
        "type": "reflection",
        "observer": observer_id,
        "content": {
            "summary": field_state.get("reflection_summary", "No summary."),
            "sqi": field_state.get("sqi_metrics", {}),
            "nodes": len(field_state.get("nodes", [])),
            "glyphs": len(field_state.get("glyphs", [])),
            "tags": field_state.get("reflection_tags", []),
        }
    }

    try:
        inject_scroll(reflection_scroll)
        kg_writer.write_scroll(reflection_scroll)
        print(f"🪞 Reflection scroll written for observer: {observer_id}")
    except Exception as e:
        print(f"❌ Failed to write reflection scroll: {e}")

    try:
        await broadcast_qfc_state(field_state, observer_id=observer_id)
    except Exception as e:
        print(f"❌ Failed to broadcast reflection field update: {e}")