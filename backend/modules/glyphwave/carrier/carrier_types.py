# backend/modules/glyphwave/carrier/carrier_types.py

from enum import Enum


class CarrierType(str, Enum):
    """Enumerates all supported GlyphWave carrier types."""
    OPTICAL = "optical"           # e.g., laser beam or fiber-optic projection
    RADIO = "radio"               # e.g., RF transmissions (terrestrial/satellite)
    QUANTUM = "quantum"           # e.g., QKD-enabled entangled photon transmission
    SIMULATED = "simulated"       # e.g., virtualized transmission in sandbox mode
    HYBRID = "hybrid"             # Combination (e.g., optical with simulated fallback)


# Optional utility function
def is_real_world_carrier(carrier_type: CarrierType) -> bool:
    """Returns True if the carrier type is physical (non-simulated)."""
    return carrier_type in {CarrierType.OPTICAL, CarrierType.RADIO, CarrierType.QUANTUM}