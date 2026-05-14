"""
🧩 Feature Flag Module for QWave / GlyphWave / Codex / SQI

Handles environment-driven toggles that gate execution paths
across Codex ↔ Photon ↔ QWave ↔ SQI.

Supported Flags:
    - PHASE9_ENABLED
    - PHASE10_ENABLED
    - QWAVE_EXEC_ON
    - QKD_ON
    - SPE_AUTO_FUSE
    - GW_ENABLED (global GlyphWave toggle)
"""

import os

# --- QWave / Codex / SQI flags ---
def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}

PHASE9_ENABLED = _flag("PHASE9_ENABLED")
PHASE10_ENABLED = _flag("PHASE10_ENABLED")
QWAVE_EXEC_ON  = _flag("QWAVE_EXEC_ON")
QKD_ON         = _flag("QKD_ON")
SPE_AUTO_FUSE  = _flag("SPE_AUTO_FUSE")

# --- GlyphWave global toggle ---
GW_FEATURE_FLAG_ENV = "GW_ENABLED"
GW_DEFAULT_ENABLED = False  # can be overridden at runtime/constants

def gw_enabled() -> bool:
    """
    Check if GlyphWave is globally enabled via env var.
    """
    val = os.getenv(GW_FEATURE_FLAG_ENV, "")
    if not val:
        return GW_DEFAULT_ENABLED
    return val.strip().lower() in {"1", "true", "yes", "on"}

def require_glyphwave():
    """
    Hard gate for modules requiring GlyphWave to be active.
    """
    if not gw_enabled():
        raise RuntimeError("🛑 GlyphWave is disabled. Set GW_ENABLED=1 to enable this feature.")

def gw_enabled_for_context(container_id: str = "", role: str = "", tags: list[str] = []) -> bool:
    """
    Reserved for advanced container-aware or role-based feature gating.
    Currently just defers to gw_enabled().
    """
    # TODO: implement fine-grained feature enablement
    return gw_enabled()

# --- Debug dump ---
def debug_flags() -> dict:
    return {
        "PHASE9_ENABLED": PHASE9_ENABLED,
        "PHASE10_ENABLED": PHASE10_ENABLED,
        "QWAVE_EXEC_ON": QWAVE_EXEC_ON,
        "QKD_ON": QKD_ON,
        "SPE_AUTO_FUSE": SPE_AUTO_FUSE,
        "GW_ENABLED": gw_enabled(),
    }