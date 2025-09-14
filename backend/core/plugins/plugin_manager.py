# File: backend/core/plugins/plugin_manager.py

import importlib
import logging
from typing import Dict, Optional, List, Any

logger = logging.getLogger("PluginManager")

# Registry to hold active plugin instances
ACTIVE_PLUGINS: Dict[str, Any] = {}

# Mapping of plugin module paths to their class names
PLUGIN_CLASSES = {
    "backend.core.plugins.aion_engine_dock": "AIONEngineDock",
    "backend.core.plugins.codexcore_trigger_hub": "CodexCoreTriggerHub",
    "backend.core.plugins.mutation_innovation_toolkit": "MutationInnovationToolkit",
    "backend.core.plugins.tranquility_auto_iteration": "TranquilityAutoIteration",
    "backend.core.plugins.pattern_reflection_oracle": "PatternReflectionOracle",
}

def register_all_plugins() -> None:
    """
    Dynamically imports and registers all available cognition plugins.
    """
    for module_path, class_name in PLUGIN_CLASSES.items():
        try:
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)
            plugin_instance = plugin_class()
            plugin_instance.register_plugin()
            ACTIVE_PLUGINS[plugin_instance.plugin_id] = plugin_instance
            logger.info(f"[PluginManager] ✅ Registered plugin: {plugin_instance.plugin_id} — {plugin_instance.name}")
        except Exception as e:
            logger.error(f"[PluginManager] ❌ Failed to load {module_path}.{class_name}: {e}", exc_info=True)

def get_plugin(plugin_id: str) -> Optional[Any]:
    """
    Retrieve a registered plugin by its plugin_id (e.g. "C1").
    """
    return ACTIVE_PLUGINS.get(plugin_id)

def get_all_plugins() -> List[Any]:
    """
    Return a list of all active plugin instances.
    """
    return list(ACTIVE_PLUGINS.values())

def clear_plugins() -> None:
    """
    Clear the ACTIVE_PLUGINS registry.
    """
    ACTIVE_PLUGINS.clear()
    logger.info("[PluginManager] 🧹 Cleared all registered plugins.")