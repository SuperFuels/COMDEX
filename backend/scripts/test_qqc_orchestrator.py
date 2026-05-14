import asyncio
from backend.modules.qqc.qqc_orchestrator import QQCCentralKernel

async def main():
    kernel = QQCCentralKernel()
    for i in range(5):
        beam_data = {
            "beam_id": f"beam_{i}",
            "coherence": 0.6 + 0.05 * i,
            "phase_shift": 0.02 * i,
            "entropy_drift": 0.01 * (i - 2),
            "gain": 1.0 + 0.1 * i,
        }
        await kernel.run_cycle(beam_data)
    await kernel.broadcast_kernel_state()
    print("\n✅ QQC Kernel Summary:\n", kernel.last_summary)

if __name__ == "__main__":
    asyncio.run(main())