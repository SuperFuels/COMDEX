# ──────────────────────────────────────────────
#  CLI Harness / Standalone Mode
# ──────────────────────────────────────────────
import yaml

async def main():
    # Load configuration
    with open("backend/QQC/qqc_kernel_v2_config.yaml") as f:
        cfg = yaml.safe_load(f)

    qqc = QuantumQuadCore()
    await qqc.boot(mode=cfg["boot"]["mode"])  # or pass cfg entirely if needed

    for i in range(5):
        beam_data = {
            "beam_id": f"ψ_{i}",
            "coherence": 0.7 + 0.05 * i,
            "phase_shift": 0.01 * i,
            "entropy_drift": 0.02 * (i - 2),
            "gain": 1.0 + 0.1 * i,
            "timestamp": time.time(),
        }
        await qqc.run_cycle(beam_data)

    await qqc.broadcast_kernel_state()
    await qqc.teleport_state("core_alpha", "core_beta")
    print("\n🧭 Final QQC Summary:")
    print(qqc.last_summary)
    await qqc.shutdown()