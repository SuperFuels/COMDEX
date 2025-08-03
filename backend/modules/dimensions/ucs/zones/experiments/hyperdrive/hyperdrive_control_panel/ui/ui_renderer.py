# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/ui/ui_renderer.py

"""
🖥 Hyperdrive UI Renderer
----------------------------
• Provides live terminal output for Hyperdrive ECU and tuning.
• Displays drift, resonance, fields, SQI phase sync, and stage info.
"""

import sys
import shutil

def render_status_panel(tick, stage, drift_a, drift_b, resonance_a, resonance_b, fields):
    width = shutil.get_terminal_size().columns
    print("\n" + "=" * width)
    print(f"🚦 Tick: {tick} | Stage: {stage}")
    print(f"📡 Drift A: {drift_a:.4f} | Drift B: {drift_b if drift_b is not None else 'N/A'}")
    print(f"🎶 Resonance A: {resonance_a:.4f} | Resonance B: {resonance_b if resonance_b is not None else 'N/A'}")
    print(f"🌌 Fields: " + ", ".join(f"{k}={v:.2f}" for k, v in fields.items()))
    print("=" * width)

def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()