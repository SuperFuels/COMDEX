# backend/modules/dimensions/containers/__init__.py

"""
Legacy Import Shim:
Redirects all 'containers' imports to 'universal_container_system' (UCS).
Maintains backward compatibility for modules still referencing 'containers'.
"""

import warnings
from backend.modules.dimensions.universal_container_system import (
    ucs_runtime,
    geometry_loader,
    ucs_orchestrator,
    soullaw_enforcer,
    visual_integration as global_visual_integration,
)
from backend.modules.dimensions.universal_container_system.ucs_runtime import UCSRuntime
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCSGeometryLoader
from backend.modules.dimensions.universal_container_system.ucs_orchestrator import UCSOrchestrator
from backend.modules.dimensions.universal_container_system.ucs_soullaw import SoulLawEnforcer
from backend.modules.dimensions.universal_container_system.ucs_trigger_map import UCSTriggerMap
from backend.modules.dimensions.universal_container_system.ucs_visual_integration import UCSVisualIntegration

# --------------------------------------
# ⚠ Migration Notice
# --------------------------------------
warnings.warn(
    "⚠ Legacy 'containers' import detected. "
    "All imports now route to 'universal_container_system'. "
    "Please refactor to use 'backend.modules.dimensions.universal_container_system' directly.",
    DeprecationWarning,
    stacklevel=2,
)

# --------------------------------------
# ✅ Singletons for Legacy Compatibility
# --------------------------------------
runtime = ucs_runtime                          # Use the already-initialized UCS runtime
geometry_loader = geometry_loader              # Shared geometry loader
orchestrator = ucs_orchestrator                # Orchestrator bound to runtime
soul_law = soullaw_enforcer                    # SoulLaw enforcement
trigger_map = UCSTriggerMap()                  # Local trigger map
visual_integration = UCSVisualIntegration(runtime=ucs_runtime)  # ✅ FIXED: Pass runtime explicitly

# --------------------------------------
# 🔄 Exports for Backward Compatibility
# --------------------------------------
__all__ = [
    "UCSRuntime",
    "UCSGeometryLoader",
    "UCSOrchestrator",
    "SoulLawEnforcer",
    "UCSTriggerMap",
    "UCSVisualIntegration",
    "runtime",
    "geometry_loader",
    "orchestrator",
    "soul_law",
    "trigger_map",
    "visual_integration",
]