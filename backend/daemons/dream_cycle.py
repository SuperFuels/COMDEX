#!/usr/bin/env python3
"""
Night-Cycle Dream Loop
Aion synthetic cognition mutations during rest windows.
"""

import time
import random
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("dream_cycle")

try:
    from backend.modules.patterns.pattern_engine import _pattern_engine
except Exception:
    raise RuntimeError("Dream cycle requires pattern engine importable")

# SCI signal bus
try:
    from backend.modules.aion_language.sci_overlay import sci_emit
except Exception:
    def sci_emit(*a, **k): pass

# ✅ Stability curve tracker
try:
    from backend.modules.sqi.sqi_stability_trace import record_sqi_delta
except Exception:
    def record_sqi_delta(*a, **k): pass

SLEEP_INTERVAL = 4.0        # seconds between dream mutations
SESSION_LENGTH = 60 * 5     # ~5-minute default dream window

def is_night_cycle() -> bool:
    """Naive night detector - Phase 1 (circadian scheduler later)"""
    hr = datetime.now().hour
    return hr >= 23 or hr <= 6  # 11pm-6am

def dream_mutate_once():
    """Pick a pattern and mutation-walk it"""
    patterns = _pattern_engine.registry.get_all_patterns()
    if not patterns:
        return

    base = random.choice(patterns).to_dict()
    origin = base.get("sqi_score", 0.3)

    mutated = _pattern_engine.mutate_pattern(base)
    new = mutated.get("sqi_score", origin)
    delta = round(new - origin, 4)

    logger.info(f"[dream] {base['name']} -> {mutated['name']} Δ={delta:+.3f}")

    # ✅ SCI event
    sci_emit("dream_mutation", {
        "origin": base["pattern_id"],
        "mutated": mutated.get("pattern_id"),
        "name": base["name"],
        "delta": delta,
        "sqi_origin": origin,
        "sqi_new": new,
        "timestamp": time.time(),
        "cycle": "dream"
    })

    # ✅ Feed stability curve (dream source)
    record_sqi_delta(delta, source="dream")

def run_dream_session():
    logger.info("🌙 entering dream cycle")

    end = datetime.now() + timedelta(seconds=SESSION_LENGTH)

    while datetime.now() < end:
        dream_mutate_once()
        time.sleep(SLEEP_INTERVAL)

    logger.info("☀️ dream cycle exit")

def main_forever():
    logger.info("🌌 Dream daemon boot")
    while True:
        if is_night_cycle():
            run_dream_session()

        time.sleep(60)  # check hourly window each minute

if __name__ == "__main__":
    try:
        main_forever()
    except KeyboardInterrupt:
        print("\nbye\n")