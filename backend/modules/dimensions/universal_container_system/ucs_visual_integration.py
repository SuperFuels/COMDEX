"""
🎨 GHX Visual Integration for UCS
-----------------------------------------------------
Connects UCS containers (Tesseract, Quantum Orb, etc.) to GHXVisualizer.
Handles:
    • Auto-injection of container geometries into GHX
    • Runtime highlight when UCS containers are executed
    • Legacy-safe: works directly with UCSRuntime + GHXVisualizer
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.modules.dimensions.universal_container_system.ucs_runtime import UCSRuntime
    from backend.modules.ghx.ghx_visualizer import GHXVisualizer

class GHXHooks:
    def __init__(self, runtime: "UCSRuntime"):
        self.runtime = runtime

    # ---------------------------------------------------------
    # 🖼 Inject Geometry + Metadata into GHXVisualizer
    # ---------------------------------------------------------
    def inject_into_visualizer(self, visualizer: "GHXVisualizer"):
        """
        Registers all UCS geometries (Tesseract, Quantum Orb, etc.) into GHXVisualizer.
        Pulls from UCSRuntime's geometry loader.
        """
        for name, meta in self.runtime.geometry_loader.geometries.items():
            visualizer.register_geometry(
                name,
                meta.get("symbol", "❔"),
                meta.get("description", f"Geometry for {name}")
            )

    # ---------------------------------------------------------
    # 🌟 Highlight Containers in GHX During Runtime
    # ---------------------------------------------------------
    def highlight_container(self, container_name: str):
        """
        Highlights a container in GHX when it is run.
        Mirrors the behavior of UCSRuntime.visualizer.highlight().
        """
        print(f"🎨 GHX: Highlighting container '{container_name}' in 3D view.")
        self.runtime.visualizer.highlight(container_name)

    # ---------------------------------------------------------
    # 🔄 Sync GHX with Runtime Containers
    # ---------------------------------------------------------
    def sync_all_containers(self):
        """
        Syncs all currently loaded UCS containers into GHXVisualizer.
        Useful if GHX is reloaded or containers are dynamically added.
        """
        print(f"🔄 GHX: Syncing {len(self.runtime.containers)} containers to GHXVisualizer...")
        for name, container_data in self.runtime.containers.items():
            self.runtime.visualizer.add_container(container_data)