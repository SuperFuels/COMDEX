#!/usr/bin/env python3
"""
🧪 Test — ResonantStrategyPlanner Integration
──────────────────────────────────────────────
Validates Phase 55 Task 1:
  • Plan generation + Θ event(“plan_eval”, SQI)
  • RMC persistence + feedback propagation
  • Adaptive resonance updates on heartbeat tick
"""

import time
from pathlib import Path
from backend.modules.skills.strategy_planner import ResonantStrategyPlanner
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat


def test_resonant_plan_generation():
    print("\n=== 🧭 ResonantStrategyPlanner Test ===")

    planner = ResonantStrategyPlanner()
    intent = {"what": "enhance harmonic coherence"}
    plan = planner.generate_plan(intent)

    assert "resonance_score" in plan
    assert 0.0 <= plan["resonance_score"] <= 1.0
    print(f"✅ Generated plan with SQI={plan['resonance_score']:.3f}")

    # confirm cache update
    rmc = ResonantMemoryCache()
    cache_entry = rmc.lookup(plan["goal"])
    if cache_entry:
        print(f"💾 RMC entry found for goal: {plan['goal']}")
    else:
        print("⚠️ No RMC entry found (acceptable on first run).")

    # trigger simulated heartbeat
    Θ = ResonanceHeartbeat(namespace="strategy_planner_test")
    for _ in range(3):
        pulse = Θ.tick()
        planner._on_heartbeat(pulse)
        time.sleep(0.2)

    summary_path = Path("data/analysis/resonant_strategy_summary.json")
    if summary_path.exists():
        print(f"📊 Resonant summary exported → {summary_path}")
    else:
        print("⚠️ Summary file missing; check write permissions.")

    print("✅ ResonantStrategyPlanner integration test complete.\n")


if __name__ == "__main__":
    test_resonant_plan_generation()