"""
🧮 Universal Container System (UCS) – Initialization
-----------------------------------------------------
Exposes the full Universal Container System runtime:
    • Tesseract Central Command (Capital container)
    • Exotic Geometry Containers (Quantum Orb, Vortex, Black Hole, Torus, etc.)
    • Multi-Container Orchestration (Quantum → Vortex → Compression → Exhaust)
    • GHX Visualizer & Knowledge Graph Integration
    • SoulLaw Enforcement Layer (safety + access control)

Usage:
    from backend.modules.dimensions.universal_container_system import (
        ucs_runtime,
        ucs_orchestrator,
        geometry_loader,
        soullaw_enforcer,
        ghx_hooks
    )
"""

import logging

# Core runtime + orchestration
from .ucs_runtime import UCSRuntime
from .ucs_orchestrator import UCSOrchestrator

# Geometry loader (Tesseract + Exotic Containers)
from .ucs_geometry_loader import GeometryLoader

# SoulLaw enforcement (symbolic ethics/safety)
from .ucs_soullaw import SoulLawEnforcer

# Visual + Knowledge Graph integration
from .ucs_visual_integration import GHXHooks

# --------------------------------------------------
# Initialize core singletons
# --------------------------------------------------
ucs_runtime = UCSRuntime()
ucs_orchestrator = UCSOrchestrator(runtime=ucs_runtime)
geometry_loader = GeometryLoader(runtime=ucs_runtime)
soullaw_enforcer = SoulLawEnforcer()
ghx_hooks = GHXHooks()

# --------------------------------------------------
# Auto-register geometries at import (Tesseract + Exotic Containers)
# --------------------------------------------------
geometry_loader.register_default_geometries(ucs_runtime)
logging.info("✅ UCS Geometry Loader initialized with default geometries.")

# --------------------------------------------------
# Bind GHX + KnowledgeGraph visualization hooks
# --------------------------------------------------
ghx_hooks.bind_runtime(ucs_runtime)
logging.info("🌌 GHXVisualizer hooks bound to UCS runtime.")

# --------------------------------------------------
# Debug logging toggle
# --------------------------------------------------
DEBUG_MODE = False
if DEBUG_MODE:
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("🛠 UCS Debug Mode Enabled: Verbose container orchestration logs active.")

# --------------------------------------------------
# Exported symbols
# --------------------------------------------------
__all__ = [
    "ucs_runtime",
    "ucs_orchestrator",
    "geometry_loader",
    "soullaw_enforcer",
    "ghx_hooks",
    "UCSRuntime",
    "UCSOrchestrator",
    "GeometryLoader",
    "SoulLawEnforcer",
    "GHXHooks",
]