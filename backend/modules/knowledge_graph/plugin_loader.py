# 📄 plugin_loader.py
#
# 🧠 Dynamic Symbolic Plugin Loader
# Loads symbolic plugins at runtime from the recommended GlyphPlugin directory
# and registers their metadata into the PluginIndex for traceability and system integration.
#
# Design Rubric:
# - 🔌 Dynamic Import + Runtime Registry .......... ✅
# - 📦 Plugin Directory Scanning .................. ✅
# - 🧠 Metadata-Aware Registration ................ ✅
# - 🔁 Trace Logging via PluginIndex .............. ✅
# - 🧩 .dc Container Compatibility (via plugin_index) ✅

import importlib.util
import os
from typing import Optional, Dict, Any

from backend.modules.knowledge_graph.indexes.plugin_index import (
    register_plugin,
    record_plugin_activity,
)

# 📁 Recommended plugin location
PLUGIN_DIRECTORY = "backend/modules/plugins/"

# 🔐 Runtime plugin cache: name → module
_loaded_runtime_plugins: Dict[str, Any] = {}


def load_plugin_from_file(file_path: str, plugin_name: str) -> Optional[Any]:
    """
    🔌 Dynamically load a plugin Python module from a file path.
    Registers the plugin into the runtime index and activity log.
    """
    if not os.path.exists(file_path):
        return None

    spec = importlib.util.spec_from_file_location(plugin_name, file_path)
    if not spec or not spec.loader:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    _loaded_runtime_plugins[plugin_name] = module
    record_plugin_activity(plugin_name, "load", f"Loaded from {file_path}")
    return module


def initialize_plugin_registry():
    """
    🧩 Preload and register all symbolic plugins from the default plugin directory.
    Plugin modules can expose `PLUGIN_METADATA` to register into PluginIndex.
    """
    for filename in os.listdir(PLUGIN_DIRECTORY):
        if filename.endswith(".py") and not filename.startswith("_"):
            path = os.path.join(PLUGIN_DIRECTORY, filename)
            name = filename[:-3]
            plugin = load_plugin_from_file(path, name)

            if plugin:
                meta = getattr(plugin, "PLUGIN_METADATA", None)
                if isinstance(meta, dict):
                    register_plugin(**meta)