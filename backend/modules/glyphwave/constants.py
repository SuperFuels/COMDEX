"""
GlyphWave constants & enums (lightweight).
"""
from enum import Enum

GW_FEATURE_FLAG_ENV = "GW_ENABLED"          # "1"/"true" enables GlyphWave
GW_DEFAULT_ENABLED = False

# default phase/frequency ranges (abstract units for sim)
DEFAULT_FREQ_HZ = 1_000.0
DEFAULT_PHASE_RAD = 0.0
DEFAULT_COHERENCE = 1.0    # 0..1

class QoSTier(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"