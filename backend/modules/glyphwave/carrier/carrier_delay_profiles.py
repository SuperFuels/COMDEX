# backend/modules/glyphwave/carrier/carrier_delay_profiles.py

import random
import time
from enum import Enum
from .carrier_types import CarrierType

# Simulated average latency ranges (in milliseconds)
CARRIER_LATENCY_PROFILES = {
    CarrierType.QUANTUM: (2, 5),       # ultra-low, high coherence
    CarrierType.OPTICAL: (5, 15),      # fast, spatially stable
    CarrierType.RADIO: (30, 100),      # longer-range, less stable
    CarrierType.SIMULATED: (1, 3),     # near-zero in virtual space
}


def simulate_carrier_delay(carrier: CarrierType, simulate: bool = True) -> float:
    """
    Applies a randomized delay to mimic carrier transmission time.
    Returns the delay used (ms). Can be disabled for testing.
    """
    if carrier not in CARRIER_LATENCY_PROFILES:
        return 0.0

    min_delay, max_delay = CARRIER_LATENCY_PROFILES[carrier]
    delay_ms = random.uniform(min_delay, max_delay)

    if simulate:
        time.sleep(delay_ms / 1000.0)  # Convert ms -> seconds

    return delay_ms