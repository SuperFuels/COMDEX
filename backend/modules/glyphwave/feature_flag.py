"""
Feature flag helper for GlyphWave.
"""
import os
from .constants import GW_FEATURE_FLAG_ENV, GW_DEFAULT_ENABLED

def gw_enabled() -> bool:
    val = os.getenv(GW_FEATURE_FLAG_ENV, "")
    if not val:
        return GW_DEFAULT_ENABLED
    return val.strip().lower() in {"1", "true", "yes", "on"}