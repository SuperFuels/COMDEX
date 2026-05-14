"""
🎨 GHX Visual Integration for UCS
-----------------------------------------------------
Connects UCS containers (Tesseract, Quantum Orb, etc.) to GHXVisualizer.
Handles:
    * Auto-injection of container geometries into GHX
    * Runtime highlight when UCS containers are executed
    * Legacy-safe: works directly with UCSRuntime
    * Backend-safe: stores sync state for frontend GHXVisualizer (React)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.modules.dimensions.universal_container_system.ucs_runtime import UCSRuntime


# ────────────────────────────────────────────────
# Quiet gate (tests/imports)
# ────────────────────────────────────────────────
_QUIET = os.getenv("TESSARIS_TEST_QUIET", "") == "1"

try:
    # Prefer shared helper if present (optional).
    from backend.utils.quiet import qprint as _qprint  # type: ignore
except Exception:  # pragma: no cover
    _qprint = None  # type: ignore


def _emit(msg: str) -> None:
    if _QUIET:
        return
    if _qprint is not None:
        _qprint(msg)
    else:
        print(msg)


class UCSVisualIntegration:
    def __init__(self, runtime: "UCSRuntime"):
        self.runtime = runtime
        self.synced_geometries = {}
        self.synced_containers = {}

    # ---------------------------------------------------------
    # 🖼 Geometry Registration (Backend Store for Frontend GHX)
    # ---------------------------------------------------------
    def inject_into_visualizer(self, visualizer=None):
        """
        Instead of directly calling frontend GHXVisualizer,
        we log and store geometry metadata for WebSocket or API sync.
        """
        self.synced_geometries = self.runtime.geometry_loader.geometries.copy()
        _emit(f"✅ GHX: {len(self.synced_geometries)} geometries stored for frontend GHXVisualizer.")

    # ---------------------------------------------------------
    # 🌟 Highlight Containers (Backend Event Log)
    # ---------------------------------------------------------
    def highlight_container(self, container_name: str):
        """
        Logs highlight events for GHXVisualizer frontend to pick up.
        """
        _emit(f"🎨 GHX: Highlight event triggered for container '{container_name}'.")
        # Store last highlight event for frontend pull/WebSocket
        self.runtime.last_highlighted_container = container_name

    # ---------------------------------------------------------
    # 🔄 Sync Runtime Containers to GHXVisualizer (Frontend)
    # ---------------------------------------------------------
    def sync_all_containers(self):
        """
        Mirror loaded UCS containers for GHXVisualizer (React frontend).
        """
        self.synced_containers = self.runtime.containers.copy()
        _emit(f"🔄 GHX: Synced {len(self.synced_containers)} UCS containers for GHXVisualizer.")
