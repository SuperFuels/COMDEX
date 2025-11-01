#!/usr/bin/env python3
# ──────────────────────────────────────────────
#  Tessaris * Quantum Quad Core (QQC) - Repair Cycle Test Harness
#  Tests rollback / SoulLaw veto / ψ-κ-T restoration logic
# ──────────────────────────────────────────────

import asyncio
import json
import os
import random
import time

from backend.QQC.qqc_central_kernel import QQCCentralKernel
from backend.QQC.qqc_repair_manager import SQI_THRESHOLD, LEDGER_PATH

# ──────────────────────────────────────────────
#  Utility
# ──────────────────────────────────────────────
def print_banner(title: str):
    print("\n" + "─" * 60)
    print(f"🧩 {title}")
    print("─" * 60)

# ──────────────────────────────────────────────
#  Test Routine
# ──────────────────────────────────────────────
async def main():
    print_banner("QQC Repair Manager - Rollback & Stabilization Test")

    # Ensure ledger directory exists
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)

    # Initialize QQC kernel (auto-creates HST + controllers)
    kernel = QQCCentralKernel()
    print(f"Session -> {kernel.session_id}")

    # Generate initial stable cycles
    print_banner("Stage 1 - Generating stable coherence cycles")
    for i in range(3):
        beam_data = {
            "beam_id": f"beam_stable_{i}",
            "coherence": 0.9 + 0.02 * random.random(),
            "phase_shift": 0.01 * i,
            "entropy_drift": 0.0,
            "gain": 1.0,
            "timestamp": time.time(),
        }
        summary = await kernel.run_cycle(beam_data)
        print(f"Cycle {i} | ⌀C={summary['avg_coherence']:.3f} | SQI={summary['txn']['C_total']:.3f}")

    # Introduce artificial instability (force SQI below threshold)
    print_banner("Stage 2 - Forcing instability (SQI < threshold)")
    unstable_beam = {
        "beam_id": "beam_unstable",
        "coherence": SQI_THRESHOLD - 0.2,   # deliberately low
        "phase_shift": 0.15,
        "entropy_drift": 0.4,
        "gain": 0.8,
        "timestamp": time.time(),
    }
    summary = await kernel.run_cycle(unstable_beam)
    sqi = summary["txn"]["C_total"]
    print(f"🚨 Instability injected | SQI={sqi:.3f} (<{SQI_THRESHOLD})")

    # Run another cycle to trigger repair manager
    print_banner("Stage 3 - Running repair cycle")
    repair_status = summary.get("repair", {})
    print(f"Repair Status: {repair_status.get('status', 'n/a')} | Restored={repair_status.get('restored')}")

    # Print summary of current holographic state
    print_banner("Stage 4 - Final QQC Kernel Summary")
    final_state = kernel.last_summary or {}
    print(json.dumps(final_state, indent=2))

    # Verify ledger content
    print_banner("Stage 5 - Ledger Snapshot")
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f.readlines() if line.strip()]
        print(f"📜 Ledger entries: {len(lines)}")
        last_entry = lines[-1]
        print(f"Last entry SQI={last_entry.get('C_total'):.3f}, Status={last_entry.get('status')}")
    else:
        print("⚠️ No ledger file found!")

# ──────────────────────────────────────────────
#  Entrypoint
# ──────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main())