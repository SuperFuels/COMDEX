# backend/modules/aion_equities/constants.py
from __future__ import annotations

# 1) Payload semantic version (goes inside payloads)
PAYLOAD_VERSION = "v0.1.0"

# 2) Schema pack version (matches folder under schemas/)
SCHEMA_PACK_VERSION = "v0_1"

ALLOWED_THESIS_MODES = {
    "long",
    "short",
    "swing_short",
    "catalyst_long",
    "neutral_watch",
}

# Placeholder thresholds (documented + tweakable; not enforced globally yet)
DEFAULT_POLICY_THRESHOLDS = {
    "bqs_min": 0.60,
    "acs_min": 0.65,
    "sqi_coherence_min": 0.65,
    "max_drift_score": 0.35,
    "max_contradiction_pressure": 0.40,
}