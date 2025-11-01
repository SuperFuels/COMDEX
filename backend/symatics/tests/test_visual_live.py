# ──────────────────────────────────────────────────────────────
# Tessaris Symatics - Δ-Telemetry Live Visualization Test
# Verifies live CodexRender animation loop.
# ──────────────────────────────────────────────────────────────

import sys, os, time, threading, numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.modules.codex.codex_render import CodexRender, record_event


def simulate_telemetry():
    """Emit λ, E, and C events asynchronously for live plotting."""
    for t in range(150):
        λ = 0.8 + 0.2 * np.sin(t / 12)
        E = 1.0 - 0.004 * t + 0.02 * np.cos(t / 20)
        C = np.exp(-0.008 * t) + 0.03 * np.random.randn()
        record_event("law_weight_update", new_weight=λ)
        record_event("wave_energy", value=E)
        record_event("coherence_index", value=C)
        time.sleep(0.05)


if __name__ == "__main__":
    renderer = CodexRender()
    thread = threading.Thread(target=simulate_telemetry, daemon=True)
    thread.start()

    # Run for 10 s; window closes automatically afterward
    renderer.live_mode(interval=0.5, duration=10.0)
    