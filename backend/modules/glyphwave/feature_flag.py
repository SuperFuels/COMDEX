# backend/modules/glyphwave/feature_flag.py

"""
Feature flag helper for GlyphWave.
"""

import os
from .constants import GW_FEATURE_FLAG_ENV, GW_DEFAULT_ENABLED


def gw_enabled() -> bool:
    """
    Lightweight environment check for GlyphWave enablement.
    Respects 'GW_ENABLED' env var.
    """
    val = os.getenv(GW_FEATURE_FLAG_ENV, "")
    if not val:
        return GW_DEFAULT_ENABLED
    return val.strip().lower() in {"1", "true", "yes", "on"}


def require_glyphwave():
    """
    Raises an error if GlyphWave is not enabled.
    Used to hard-block execution of critical modules.
    """
    if not gw_enabled():
        raise RuntimeError("GlyphWave is disabled — set GW_ENABLED=1 to enable.")


# Reserved for future use
# def gw_enabled_for_container(container_id: str, container_class: str = "") -> bool:
#     """ Optional per-container override logic """
#     return gw_enabled()