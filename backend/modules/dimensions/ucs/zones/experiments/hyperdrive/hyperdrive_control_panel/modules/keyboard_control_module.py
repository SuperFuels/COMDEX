import sys
import termios
import tty
import threading
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_controller_module import SQIController

def getch():
    """Capture single-key input (Linux/Mac)."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def keyboard_control(engine, sqi: SQIController):
    """
    Maps keyboard shortcuts to engine control:
    w/s: Manual resonance adjust
    z: Auto warp ramp (SQI-driven)
    x: Abort warp ramp
    o: Auto optimize (SQI-driven)
    t: Toggle SQI feedback loop
    r: Reset drift filters
    1–5: Quick-load SQI profiles (85, 90, 95, 99, 100)
    p: Save current state profile
    q: Export best state & quit
    """
    while True:
        key = getch()

        if key == "w":
            engine.resonance_phase += 0.2
            engine.log_event("Manual: Resonance increased (+0.2).")

        elif key == "s":
            engine.resonance_phase -= 0.2
            engine.log_event("Manual: Resonance decreased (-0.2).")

        elif key == "z":
            threading.Thread(target=sqi.auto_warp_ramp, daemon=True).start()

        elif key == "x":
            engine.auto_sequence = False
            engine.log_event("Manual: Warp ramp aborted.")

        elif key == "o":
            threading.Thread(target=sqi.auto_optimize, daemon=True).start()

        elif key == "t":
            engine.sqi_enabled = not engine.sqi_enabled
            engine.log_event(f"SQI {'enabled' if engine.sqi_enabled else 'disabled'} manually.")

        elif key == "r":
            engine.resonance_filtered.clear()
            engine.log_event("🔄 Drift filters reset.")

        elif key in ["1", "2", "3", "4", "5"]:
            stage_map = {"1": 85, "2": 90, "3": 95, "4": 99, "5": 100}
            stage = stage_map[key]
            sqi.set_target(stage)
            engine.log_event(f"📂 Quick-loaded SQI profile target: {stage}%")

        elif key == "p":
            engine._export_best_state()
            engine.log_event("💾 Profile saved from current engine state.")

        elif key == "q":
            engine._export_best_state()
            engine.log_event("💾 Final state exported. Exiting...")
            sys.exit(0)