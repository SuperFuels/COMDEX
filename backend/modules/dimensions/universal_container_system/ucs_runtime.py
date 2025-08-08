"""
🧮 UCS Runtime
-----------------------------------------------------
Handles:
    • Container loading/execution
    • GHXVisualizer integration
    • SQI runtime + Pi GPIO event output
    • SoulLaw enforcement
    • Geometry registration + trigger map events
    • Legacy container_runtime API compatibility
"""

import json
import os
import time
from typing import Dict, Any

from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCSGeometryLoader
from backend.modules.dimensions.universal_container_system.ucs_soullaw import SoulLawEnforcer
from backend.modules.dimensions.universal_container_system.ucs_trigger_map import UCSTriggerMap
# Stub GHXVisualizer (frontend-only)
class GHXVisualizer:
    def add_container(self, container): 
        print(f"[GHXVisualizer] (stub) Added container {container.get('name')}")
    def highlight(self, name): 
        print(f"[GHXVisualizer] (stub) Highlighting {name}")
    # NEW: quiet the AttributeError; callers expect this hook
    def log_event(self, *args, **kwargs):
        # keep as no-op or uncomment for visibility
        # print(f"[GHXVisualizer] (stub) log_event {args} {kwargs}")
        pass

class UCSRuntime:
    def __init__(self):
        self.containers: Dict[str, Dict[str, Any]] = {}

        # ✅ SQIRuntime alias defined post-class to avoid circular import
        self.sqi = None  
        self.visualizer = GHXVisualizer()
        self.geometry_loader = UCSGeometryLoader()
        self.soul_law = SoulLawEnforcer()
        self.trigger_map = UCSTriggerMap()

    # ---------------------------------------------------------
    # 🔑 Load and Manage Containers
    # ---------------------------------------------------------
    def load_container(self, path: str) -> str:
        """Load a .dc.json container into UCS runtime."""
        with open(path, 'r') as f:
            container_data = json.load(f)

        name = container_data.get("name") or os.path.basename(path).replace(".dc.json", "")
        self.containers[name] = container_data

        # Geometry + Visualization
        self.geometry_loader.register_geometry(name, container_data.get("geometry", "default"))
        self.visualizer.add_container(container_data)

        print(f"✅ Loaded container: {name}")
        return name

    def save_container(self, name: str, data: Dict[str, Any]):
        """Save container state into runtime memory."""
        self.containers[name] = data

    def get_container(self, name: str) -> Dict[str, Any]:
        """Retrieve container state."""
        return self.containers.get(name, {})

    # ---------------------------------------------------------
    # 🚀 Runtime Execution
    # ---------------------------------------------------------
    def run_container(self, name: str):
        """Execute a container's symbolic runtime."""
        if name not in self.containers:
            raise ValueError(f"Container '{name}' not loaded.")
        container = self.containers[name]
        print(f"🚀 Running container: {name}")

        # 🛡 SoulLaw enforcement
        self.soul_law.validate_access(container)

        # 🔥 Trigger glyph-based events
        for glyph in container.get("glyphs", []):
            if glyph in self.trigger_map.map:
                event = self.trigger_map.map[glyph]
                self.emit_event(event, container)

        # 🎨 GHX Visualization highlight
        self.visualizer.highlight(name)

    def run_all(self):
        """Run all loaded containers sequentially (basic orchestration)."""
        for name in self.containers.keys():
            self.run_container(name)
            time.sleep(0.5)  # pacing for visual clarity

    # ---------------------------------------------------------
    # ⚡ Event & SQI Integration
    # ---------------------------------------------------------
    def emit_event(self, event_name: str, container: dict):
        """Emit an event into SQI runtime (GPIO-capable for Pi testbench)."""
        print(f"⚡ Emitting event: {event_name} from {container['name']}")
        if self.sqi:
            self.sqi.emit(event_name, payload={"container": container})

    # ---------------------------------------------------------
    # 🧩 Expansion / Collapse (Legacy API Compatibility)
    # ---------------------------------------------------------
    def expand_container(self, name: str):
        """Expand container (legacy alias)."""
        c = self.get_container(name)
        c["state"] = "expanded"
        self.save_container(name, c)
        return c

    def collapse_container(self, name: str):
        """Collapse container (legacy alias)."""
        c = self.get_container(name)
        c["state"] = "collapsed"
        self.save_container(name, c)
        return c

    def load_dc_container(self, name: str):
        """Alias for legacy container loading (returns runtime memory container)."""
        return self.get_container(name)

    def embed_glyph_block_into_container(self, name: str, glyph_block: Any):
        """Embed glyph block (legacy alias for Codex injection)."""
        c = self.get_container(name)
        c.setdefault("glyphs", []).append(glyph_block)
        self.save_container(name, c)


# ---------------------------------------------------------
# ✅ Singleton + Legacy Aliases
# ---------------------------------------------------------
ucs_runtime = UCSRuntime()

# ✅ Define SQIRuntime alias after UCSRuntime definition to avoid circular import
SQIRuntime = UCSRuntime  
ucs_runtime.sqi = SQIRuntime()

# Legacy compatibility shims
load_dc_container = ucs_runtime.load_dc_container
expand_container = ucs_runtime.expand_container
collapse_container = ucs_runtime.collapse_container
embed_glyph_block_into_container = ucs_runtime.embed_glyph_block_into_container

__all__ = [
    "UCSRuntime",
    "ucs_runtime",
    "load_dc_container",
    "expand_container",
    "collapse_container",
    "embed_glyph_block_into_container",
]

# ---------------------------------------------------------
# ✅ Singleton + Legacy Aliases
# ---------------------------------------------------------
ucs_runtime = UCSRuntime()

# ✅ Define SQIRuntime alias after UCSRuntime definition to avoid circular import
SQIRuntime = UCSRuntime  
ucs_runtime.sqi = SQIRuntime()

# Legacy compatibility shims
load_dc_container = ucs_runtime.load_dc_container
expand_container = ucs_runtime.expand_container
collapse_container = ucs_runtime.collapse_container
embed_glyph_block_into_container = ucs_runtime.embed_glyph_block_into_container

# ✅ NEW: Provide accessor for imports expecting get_ucs_runtime()
def get_ucs_runtime() -> UCSRuntime:
    """Return the global UCS runtime singleton (for vault + hyperdrive)."""
    return ucs_runtime

__all__ = [
    "UCSRuntime",
    "ucs_runtime",
    "get_ucs_runtime",  # ✅ Exported now
    "load_dc_container",
    "expand_container",
    "collapse_container",
    "embed_glyph_block_into_container",
]