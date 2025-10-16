# ──────────────────────────────────────────────
#  Tessaris • QQC Test Harness (v0.2)
#  Verifies Two-Phase Commit and ψ–κ–T regulation
# ──────────────────────────────────────────────

import asyncio
import time
import os
from backend.QQC.qqc_central_kernel import QQCCentralKernel

async def main():
    kernel = QQCCentralKernel()

    # Simulated LightWave beam stream
    beam_sequence = [
        {"beam_id": f"beam_{i}",
         "coherence": 0.7 + 0.05 * i,
         "phase_shift": 0.01 * i,
         "entropy_drift": 0.02 * (i - 2),
         "gain": 1.0 + 0.1 * i,
         "timestamp": time.time()}
        for i in range(6)
    ]

    print("⚙️ Running QQC feedback cycles...")
    for beam_data in beam_sequence:
        summary = await kernel.run_cycle(beam_data)
        print(f"Cycle {beam_data['beam_id']} → ⌀C={summary['avg_coherence']:.3f} | SQI={summary['txn']['C_total']:.3f}")
        await asyncio.sleep(0.05)

    # Display summary
    print("\n🧠 QQC Kernel Final Summary:")
    print(kernel.last_summary)

    # Verify ledger existence
    ledger_path = "data/ledger/qqc_commit_log.jsonl"
    if os.path.exists(ledger_path):
        lines = sum(1 for _ in open(ledger_path))
        print(f"📜 Ledger entries: {lines}")
    else:
        print("⚠️ Ledger not found.")

if __name__ == "__main__":
    asyncio.run(main())