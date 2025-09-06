"""
🧩 GlyphWave Feature Flag Module

Handles enablement of GlyphWave features based on environment variables.

Env Var:
    - `GW_ENABLED` — global switch (default: False unless overridden in `constants.py`)
"""

import os
from .constants import GW_FEATURE_FLAG_ENV, GW_DEFAULT_ENABLED


def gw_enabled() -> bool:
    """
    Check if GlyphWave is globally enabled via env var.

    Returns:
        bool: True if enabled, else False.
    """
    val = os.getenv(GW_FEATURE_FLAG_ENV, "")
    if not val:
        return GW_DEFAULT_ENABLED
    return val.strip().lower() in {"1", "true", "yes", "on"}


def require_glyphwave():
    """
    Hard gate for modules requiring GlyphWave to be active.

    Raises:
        RuntimeError: If GlyphWave is not enabled.
    """
    if not gw_enabled():
        raise RuntimeError("🛑 GlyphWave is disabled. Set GW_ENABLED=1 to enable this feature.")


def gw_enabled_for_context(container_id: str = "", role: str = "", tags: list[str] = []) -> bool:
    """
    Reserved for advanced container-aware or role-based feature gating.

    Args:
        container_id (str): Optional container ID
        role (str): Optional execution role
        tags (list[str]): Optional symbolic tags

    Returns:
        bool: True if enabled for this context
    """
    # TODO: implement fine-grained feature enablement
    return gw_enabled()