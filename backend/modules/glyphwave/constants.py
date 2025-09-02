"""
GlyphWave constants & enums (lightweight).
"""

from enum import Enum

# ════════════════════════════════════════════════════════════════
# 🌐 GlyphWave Feature Flag
# ════════════════════════════════════════════════════════════════
GW_FEATURE_FLAG_ENV = "GW_ENABLED"          # "1"/"true" enables GlyphWave
GW_DEFAULT_ENABLED = False

# ════════════════════════════════════════════════════════════════
# ⚙️ Default Sim Parameters
# ════════════════════════════════════════════════════════════════
DEFAULT_FREQ_HZ = 1_000.0
DEFAULT_PHASE_RAD = 0.0
DEFAULT_COHERENCE = 1.0    # 0..1

# ════════════════════════════════════════════════════════════════
# 🏷️ QoS Tier
# ════════════════════════════════════════════════════════════════
class QoSTier(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"

# ════════════════════════════════════════════════════════════════
# 📡 Carrier Type (used in .gwip and QWave beams)
# ════════════════════════════════════════════════════════════════
class CarrierType(str, Enum):
    OPTICAL = "optical"
    RADIO = "radio"
    QUANTUM = "quantum"
    SIMULATED = "simulated"

# ════════════════════════════════════════════════════════════════
# 🧬 Beam State for QWave
# ════════════════════════════════════════════════════════════════
class BeamState(str, Enum):
    LIVE = "live"
    PREDICTED = "predicted"
    CONTRADICTED = "contradicted"
    COLLAPSED = "collapsed"

# ════════════════════════════════════════════════════════════════
# 🌈 Beam Modulation Type
# ════════════════════════════════════════════════════════════════
class ModulationType(str, Enum):
    WDM = "wdm"                   # Wavelength-division multiplexing
    QKD = "qkd"                   # Quantum key distribution
    SIM_PHASE = "sim_phase"       # Simulated phase modulation
    NONE = "none"