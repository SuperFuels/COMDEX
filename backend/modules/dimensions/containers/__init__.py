# backend/modules/dimensions/containers/__init__.py

"""
Legacy Import Shim:
Redirects all 'containers' imports to 'universal_container_system' (UCS).
Maintains backward compatibility for modules still referencing 'containers'.
"""

import warnings

# Notify developers about the migration
warnings.warn(
    "⚠ Legacy 'containers' import detected. "
    "All imports now route to 'universal_container_system'. "
    "Please refactor to use 'backend.modules.dimensions.universal_container_system' directly.",
    DeprecationWarning,
    stacklevel=2
)

# Import UCS runtime and expose it under legacy namespace
from backend.modules.dimensions.universal_container_system.ucs_runtime import UCSRuntime
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCSGeometryLoader
from backend.modules.dimensions.universal_container_system.ucs_orchestrator import UCSOrchestrator
from backend.modules.dimensions.universal_container_system.ucs_soullaw import SoulLawEnforcer
from backend.modules.dimensions.universal_container_system.ucs_trigger_map import UCSTriggerMap
from backend.modules.dimensions.universal_container_system.ucs_visual_integration import UCSVisualIntegration

# Instantiate singletons (optional global pattern for legacy use)
runtime = UCSRuntime()
geometry_loader = UCSGeometryLoader()
orchestrator = UCSOrchestrator(runtime)
soul_law = SoulLawEnforcer()
trigger_map = UCSTriggerMap()
visual_integration = UCSVisualIntegration()

# Explicit re-exports for legacy imports:
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