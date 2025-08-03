import threading
import time
import sys
import termios
import tty
from datetime import datetime

def hyperdrive_terminal(engine_a=None, engine_b=None, refresh_rate=0.5):
    """
    🖥️ Hyperdrive Terminal Panel:
    - Displays live ECU telemetry and events.
    - Auto-attaches to engines from ENGINE_REGISTRY if none passed.
    - Accepts keyboard commands for control overrides (Stage, Harmonics, SQI Lock/Unlock).
    """

    # 🔗 Auto-detect running engines if not passed explicitly
    try:
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.hyperdrive_entry import ENGINE_REGISTRY
        if engine_a is None and "engine_a" in ENGINE_REGISTRY:
            print("🔗 Auto-attached to Engine A from registry.")
            engine_a = ENGINE_REGISTRY["engine_a"]
        if engine_b is None and "engine_b" in ENGINE_REGISTRY:
            print("🔗 Auto-attached to Engine B from registry.")
            engine_b = ENGINE_REGISTRY["engine_b"]
    except ImportError:
        print("⚠ Engine registry not available. Manual engine reference required.")

    # 🚨 Ensure we actually have an engine to monitor
    if engine_a is None:
        print("❌ No engine detected. Start hyperdrive_entry first or pass engine references explicitly.")
        return

    telemetry_data = {
        "tick": 0,
        "resonance": 0.0,
        "drift": 0.0,
        "thermal": 0.0,
        "power": 0.0,
        "stability": 0.0,
        "particles": 0,
        "events": [],
        "sqi_locked": False,
        "stage": "N/A"
    }

    stop_flag = threading.Event()

    def get_keypress():
        """ Non-blocking keypress listener for terminal input. """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while not stop_flag.is_set():
                if select_ready(fd):
                    key = sys.stdin.read(1)
                    handle_key(key)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def select_ready(fd):
        import select
        r, _, _ = select.select([fd], [], [], 0.1)
        return bool(r)

    def handle_key(key):
        """ Key bindings for terminal control """
        if key.lower() == "q":
            print("\n🛑 Emergency Stop Requested.")
            stop_flag.set()
        elif key.lower() == "s":
            print("🔀 Stage Shift Triggered.")
            engine_a.transition_stage(engine_a)
            if engine_b:
                engine_b.transition_stage(engine_b)
        elif key.lower() == "h":
            print("🎼 Harmonic Resync Triggered.")
            engine_a._resync_harmonics()
        elif key.lower() == "l":
            print("📜 Last 5 Events:")
            for e in telemetry_data["events"][-5:]:
                print(f"  [{e['timestamp']}] {e['message']}")
        elif key.lower() == "k":  # 🔒 Manual SQI Lock
            if hasattr(engine_a, "handle_sqi_lock"):
                engine_a.handle_sqi_lock(telemetry_data.get("drift", 0.0))
                print("🔒 Manual SQI Lock Engaged.")
        elif key.lower() == "u":  # 🔓 SQI Unlock
            if hasattr(engine_a, "sqi_locked"):
                engine_a.sqi_locked = False
                print("🔓 SQI Lock Released.")
        else:
            print(f"❓ Unknown command: '{key}' (Controls: q=quit, s=stage, h=resync, l=log, k=lock, u=unlock)")

    def telemetry_loop():
        """ Refreshes telemetry data every refresh_rate seconds. """
        while not stop_flag.is_set():
            telemetry_data["tick"] = getattr(engine_a, "tick_count", 0)
            telemetry_data["resonance"] = getattr(engine_a, "resonance_phase", 0.0)
            telemetry_data["drift"] = (max(engine_a.resonance_filtered[-30:], default=0) -
                                       min(engine_a.resonance_filtered[-30:], default=0))
            telemetry_data["thermal"] = getattr(engine_a, "thermal_load", 0.0)
            telemetry_data["power"] = getattr(engine_a, "power_draw", 0.0)
            telemetry_data["stability"] = (1.0 - telemetry_data["drift"] * 10) if telemetry_data["drift"] else 1.0
            telemetry_data["particles"] = len(getattr(engine_a, "particles", []))
            telemetry_data["events"] = getattr(engine_a, "event_log", [])[-10:]
            telemetry_data["sqi_locked"] = getattr(engine_a, "sqi_locked", False)
            telemetry_data["stage"] = engine_a.stages[engine_a.current_stage] if hasattr(engine_a, "stages") else "N/A"

            print_panel(telemetry_data)
            time.sleep(refresh_rate)

    def print_panel(data):
        """ Clears the terminal and prints updated telemetry panel. """
        sys.stdout.write("\033[2J\033[H")  # Clear terminal
        sqi_state = "✅ LOCKED" if data["sqi_locked"] else "❌ UNLOCKED"
        print("🚀 Hyperdrive Terminal Panel (Press 'q' to Quit)")
        print(f" Tick:        {data['tick']}")
        print(f" Stage:       {data['stage']}")
        print(f" Resonance:   {data['resonance']:.4f}")
        print(f" Drift:       {data['drift']:.4f}")
        print(f" SQI:         {sqi_state}")
        print(f" Thermal:     {data['thermal']:.1f} °C")
        print(f" Power:       {data['power']:.1f} W")
        print(f" Stability:   {data['stability']:.3f}")
        print(f" Particles:   {data['particles']}")
        print("-" * 45)
        print("Recent Events:")
        for e in data["events"][-5:]:
            ts = e['timestamp'][-8:] if 'timestamp' in e else '??:??:??'
            print(f"  [{ts}] {e.get('message', 'No message')}")
        print("-" * 45)
        print("Controls: [q] Quit | [s] Stage | [h] Resync | [l] Log | [k] SQI Lock | [u] SQI Unlock")

    print("🚀 Launching Hyperdrive Terminal (Auto-attach mode)...")
    threading.Thread(target=get_keypress, daemon=True).start()
    telemetry_loop()
    print("✅ Terminal Panel Closed.")