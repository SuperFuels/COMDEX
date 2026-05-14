"""
🌐 GlyphWave Constants & Enums

Shared symbolic constants, enums, and configuration defaults
used across all GlyphWave modules (codec, scheduler, carrier, HUD, etc).
"""

from enum import Enum

# ════════════════════════════════════════════════════════════════
# 🌐 Feature Flag Environment Variable
# ════════════════════════════════════════════════════════════════
GW_FEATURE_FLAG_ENV = "GW_ENABLED"           # Set "1", "true", "yes", or "on" to activate GlyphWave
GW_DEFAULT_ENABLED = False                   # Default: disabled unless explicitly enabled

# ════════════════════════════════════════════════════════════════
# ⚙️ Default Simulation Parameters
# ════════════════════════════════════════════════════════════════
DEFAULT_FREQ_HZ = 1_000.0                    # Default frequency in Hz
DEFAULT_PHASE_RAD = 0.0                      # Default phase in radians
DEFAULT_COHERENCE = 1.0                      # Default coherence level (0.0-1.0)
DEFAULT_DRIFT_RATE = 0.01                    # Default simulated phase drift per tick
DEFAULT_JITTER_STDDEV = 0.005                # Default std deviation for phase jitter

# ════════════════════════════════════════════════════════════════
# 🏷️ QoS Tier: Traffic Prioritization
# ════════════════════════════════════════════════════════════════
class QoSTier(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"

# ════════════════════════════════════════════════════════════════
# 📡 Carrier Type: Underlying Transport Mode
# ════════════════════════════════════════════════════════════════
class CarrierType(str, Enum):
    OPTICAL = "optical"           # Real-world fiber-optic or laser carrier
    RADIO = "radio"               # Electromagnetic signal (e.g. GHz)
    QUANTUM = "quantum"           # Entangled quantum particle-based
    SIMULATED = "simulated"       # In-memory or software test mode

# ════════════════════════════════════════════════════════════════
# 🧬 Beam State: QWave Lifecycle Status
# ════════════════════════════════════════════════════════════════
class BeamState(str, Enum):
    LIVE = "live"                 # Actively propagating
    PREDICTED = "predicted"       # Not yet collapsed (forecast)
    CONTRADICTED = "contradicted" # Invalidated by logic mismatch
    COLLAPSED = "collapsed"       # Observed and resolved

# ════════════════════════════════════════════════════════════════
# 🌈 Beam Modulation Strategy
# ════════════════════════════════════════════════════════════════
class ModulationType(str, Enum):
    WDM = "wdm"                   # Wavelength-Division Multiplexing (optical)
    QKD = "qkd"                   # Quantum Key Distribution (encrypted)
    SIM_PHASE = "sim_phase"       # Software phase simulation
    TIME_LOCK = "time_lock"       # Time-delayed unlock (Tessaris/GlyphVault)
    NONE = "none"                 # No modulation

# ════════════════════════════════════════════════════════════════
# 📊 Telemetry Keys for HUD / WaveScope
# ════════════════════════════════════════════════════════════════
TELEMETRY_KEYS = {
    "emit", "capture", "modulate", "collapse", "replay", "jitter", "drift",
    "beam_state", "coherence", "qos", "carrier_type"
}