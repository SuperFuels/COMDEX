# 📄 plugin_index.py
#
# 🔌 Glyph Plugin Metadata & Lifecycle Index
# Manages plugin metadata registration, usage activity, symbolic trace logs, and
# optional toggle states. All metadata is linked into the unified IGI Knowledge Graph.
#
# Design Rubric:
# - ✅ DNA Switch Registration ....................... ✅
# - 🧠 Symbolic Plugin Metadata ...................... ✅
# - 🔁 Activity + Event Trace Logging ................ ✅
# - 📦 Integration with IndexRegistry + Container .... ✅
# - 🧩 Dashboard Compatibility (PluginManager.tsx) ... ✅

import datetime
from typing import Dict, Any, List

from backend.modules.knowledge_graph.index_registry import register_index
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# 🧬 DNA Activation: Registers this index as symbolic memory traceable
DNA_SWITCH.register(__file__)

# 🆔 Plugin Index Identifier
PLUGIN_INDEX_ID = "plugin_index"

# 📦 In-memory store
_plugin_log: List[Dict[str, Any]] = []
_loaded_plugins: Dict[str, Dict[str, Any]] = {}  # plugin_name -> metadata

# 🧠 Register with central index registry
register_index(PLUGIN_INDEX_ID, _plugin_log)


def log_plugin_event(
    *,
    plugin_name: str,
    event: str,
    description: str,
    tags: List[str] = None,
    metadata: Dict[str, Any] = None,
):
    """📝 Store lifecycle, runtime, or error events with traceable context."""
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "plugin_name": plugin_name,
        "event": event,
        "description": description,
        "tags": tags or [],
        "metadata": metadata or {},
    }
    _plugin_log.append(record)

    # Limit growth (trace pruning)
    if len(_plugin_log) > 2000:
        _plugin_log[:] = _plugin_log[-1000:]


def register_plugin(
    name: str,
    version: str,
    purpose: str,
    entry_point: str,
    tags: List[str] = None,
    enabled: bool = True,
):
    """
    🧠 Register a plugin's core metadata into the knowledge graph.
    Supports usage by PluginManager, glyph replayers, and replay renderers.
    """
    metadata = {
        "name": name,
        "version": version,
        "purpose": purpose,
        "entry_point": entry_point,
        "enabled": enabled,
        "tags": tags or [],
        "registered_at": datetime.datetime.utcnow().isoformat(),
    }
    _loaded_plugins[name] = metadata

    log_plugin_event(
        plugin_name=name,
        event="registered",
        description=f"Plugin '{name}' registered",
        tags=["plugin", "register"] + (tags or []),
        metadata=metadata,
    )


def get_loaded_plugins() -> List[Dict[str, Any]]:
    """📤 Return list of all currently loaded + registered plugins (for UI)."""
    return list(_loaded_plugins.values())


def record_plugin_activity(plugin_name: str, action: str, detail: str = ""):
    """🔁 Log symbolic runtime activity or usage trace from a plugin."""
    log_plugin_event(
        plugin_name=plugin_name,
        event="activity",
        description=detail or f"Plugin '{plugin_name}' performed action: {action}",
        tags=["plugin", "activity", action],
    )


def disable_plugin(plugin_name: str):
    """🚫 Soft-disable a plugin while preserving metadata."""
    if plugin_name in _loaded_plugins:
        _loaded_plugins[plugin_name]["enabled"] = False
        log_plugin_event(
            plugin_name=plugin_name,
            event="disabled",
            description=f"Plugin '{plugin_name}' was disabled",
            tags=["plugin", "disable"],
        )


def clear_plugin_log():
    """🧹 Clear in-memory plugin trace (for resets or debug)."""
    _plugin_log.clear()