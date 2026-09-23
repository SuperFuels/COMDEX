"""AION Device Fabric.

An additive, fail-closed runtime for representing one governed AION across a
mother node and capability-bounded device nodes.  The package deliberately has
no import-time connection to HexCore, Boardroom, or the existing Local Node
runtime; integration is performed through explicit adapters after validation.
"""

from .contracts import (
    Capability,
    CapabilityKind,
    DeviceProfile,
    NodeRole,
    RiskLevel,
)
from .runtime import AionFabricRuntime

__all__ = [
    "AionFabricRuntime",
    "Capability",
    "CapabilityKind",
    "DeviceProfile",
    "NodeRole",
    "RiskLevel",
]
