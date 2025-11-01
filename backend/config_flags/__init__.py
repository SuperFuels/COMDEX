# backend/config_flags/__init__.py
# ================================================================
#  Tessaris Config Package
# ================================================================
import os

# 🌐 Default API base URL for glyph service
GLYPH_API_BASE_URL = os.getenv("GLYPH_API_BASE_URL", "http://localhost:8080/api")

# 🧠 Logging and feature control
ENABLE_GLYPH_LOGGING = os.getenv("ENABLE_GLYPH_LOGGING", "true").lower() == "true"

# ⚛️ Symbolic-Photonic Entanglement auto-fusion (SPE)
# Enables automatic recombination of symbolic/photonic traces after drift detection
SPE_AUTO_FUSE = os.getenv("SPE_AUTO_FUSE", "true").lower() == "true"

# 📦 Data paths
DATA_DIR = os.getenv("DATA_DIR", "./data")
CACHE_DIR = os.getenv("CACHE_DIR", "./cache")

# 🔦 Feature Flags
from .feature_flags import (
    is_lightwave_enabled,
    is_qqc_enabled,
    print_feature_status,
)

__all__ = [
    "GLYPH_API_BASE_URL",
    "ENABLE_GLYPH_LOGGING",
    "SPE_AUTO_FUSE",
    "DATA_DIR",
    "CACHE_DIR",
    "is_lightwave_enabled",
    "is_qqc_enabled",
    "print_feature_status",
]