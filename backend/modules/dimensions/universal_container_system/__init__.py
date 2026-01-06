"""
🧮 Universal Container System (UCS) - Initialization
-----------------------------------------------------
Exposes the full Universal Container System runtime:
    * Tesseract Central Command (Capital container)
    * Exotic Geometry Containers (Quantum Orb, Vortex, Black Hole, Torus, etc.)
    * Multi-Container Orchestration (Quantum -> Vortex -> Compression -> Exhaust)
    * GHX Visualizer & Knowledge Graph Integration
    * SoulLaw Enforcement Layer (safety + access control)

Usage:
    from backend.modules.dimensions.universal_container_system import (
        ucs_runtime,
        ucs_orchestrator,
        geometry_loader,
        soullaw_enforcer,
        visual_integration,
        load_dc_container,
        container_loader,
    )
"""

from __future__ import annotations

import os
import logging

# --------------------------------------------------
# Quiet gate (tests/imports)
# --------------------------------------------------
_QUIET = os.getenv("TESSARIS_TEST_QUIET", "") == "1"


def _log_info(msg: str) -> None:
    if _QUIET:
        return
    logging.info(msg)


def _log_warning(msg: str) -> None:
    # Warnings are still suppressed under quiet to avoid import spam in tests.
    if _QUIET:
        return
    logging.warning(msg)


# --------------------------------------------------
# Core runtime (singleton) + orchestration
#   IMPORTANT: import the singleton from ucs_runtime
#   Do NOT instantiate UCSRuntime() again here.
# --------------------------------------------------
from .ucs_runtime import UCSRuntime, ucs_runtime, get_ucs_runtime
from .ucs_orchestrator import UCSOrchestrator

# Geometry loader (Tesseract + Exotic Containers)
from .ucs_geometry_loader import UCSGeometryLoader

# SoulLaw enforcement (symbolic ethics/safety)
from .ucs_soullaw import SoulLawEnforcer

# Visual + Knowledge Graph integration
from .ucs_visual_integration import UCSVisualIntegration

# --------------------------------------------------
# Initialize core singletons / services
#   All must reference the SAME ucs_runtime instance
# --------------------------------------------------
ucs_orchestrator = UCSOrchestrator(runtime=ucs_runtime)
geometry_loader = UCSGeometryLoader()
soullaw_enforcer = SoulLawEnforcer()
visual_integration = UCSVisualIntegration(runtime=ucs_runtime)

# --------------------------------------------------
# Auto-register geometries at import (Tesseract + Exotic Containers)
# --------------------------------------------------
try:
    # NOTE: UCSGeometryLoader.__init__ already registers defaults; keep call for legacy safety.
    geometry_loader.register_default_geometries()
    _log_info("✅ UCS Geometry Loader initialized with default geometries.")
except Exception as e:
    _log_warning(f"UCS Geometry Loader init failed: {e!r}")

# --------------------------------------------------
# Bind GHX + KnowledgeGraph visualization hooks
# --------------------------------------------------
try:
    visual_integration.inject_into_visualizer(ucs_runtime.visualizer)
    _log_info("🌌 GHXVisualizer integration bound to UCS runtime.")
except Exception as e:
    _log_warning(f"GHXVisualizer integration failed: {e!r}")

# --------------------------------------------------
# Legacy / convenience loaders
# --------------------------------------------------
def load_dc_container(path: str, register_as_atom: bool = False):
    """
    Legacy/module-level helper that routes to the runtime's loader.
    Prefers load_dc_container if present; falls back to load_container_from_path.
    """
    rt = get_ucs_runtime()
    if hasattr(rt, "load_dc_container"):
        return rt.load_dc_container(path, register_as_atom=register_as_atom)
    if hasattr(rt, "load_container_from_path"):
        return rt.load_container_from_path(path, register_as_atom=register_as_atom)
    raise AttributeError("UCSRuntime has no container load method")


# Some older code expects a callable named `container_loader`.
# Keep it as a thin shim to our module-level load_dc_container above.
try:
    from .container_loader import container_loader  # type: ignore
except Exception:
    def container_loader(path: str, register_as_atom: bool = False):
        """
        Load a .dc container via UCS runtime.
        Mirrors the expected callable used by backend/main.py.
        """
        return load_dc_container(path, register_as_atom=register_as_atom)

# --------------------------------------------------
# Debug logging toggle
# --------------------------------------------------
DEBUG_MODE = False
if DEBUG_MODE and not _QUIET:
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("🛠 UCS Debug Mode Enabled: Verbose container orchestration logs active.")

# --------------------------------------------------
# Exported symbols
# --------------------------------------------------
__all__ = [
    # Singletons / accessors
    "ucs_runtime",
    "get_ucs_runtime",

    # Services
    "ucs_orchestrator",
    "geometry_loader",
    "soullaw_enforcer",
    "visual_integration",

    # API helpers
    "load_dc_container",
    "container_loader",

    # Types
    "UCSRuntime",
    "UCSOrchestrator",
    "UCSGeometryLoader",
    "SoulLawEnforcer",
    "UCSVisualIntegration",
]
