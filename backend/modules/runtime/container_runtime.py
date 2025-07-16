# container_runtime.py

import time
import threading
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.websocket.websocket_manager import WebSocketManager  # Optional
from backend.modules.dna_chain.dna_switch import register_dna_switch

# ✅ Optional glyph summarizer
try:
    from backend.modules.glyphos.glyph_summary import summarize_glyphs
except ImportError:
    summarize_glyphs = None

class ContainerRuntime:
    def __init__(self, state_manager: StateManager, tick_interval: float = 2.0):
        self.state_manager = state_manager
        self.executor = GlyphExecutor(state_manager)
        self.tick_interval = tick_interval
        self.running = False
        self.logs = []
        self.websocket = WebSocketManager()  # Optional WebSocket feedback
        self.tick_counter = 0
        self.loop_enabled = False
        self.loop_interval = 50  # How many ticks before looping
        self.rewind_buffer = []
        self.max_rewind = 5  # Store last 5 container states

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.run_loop, daemon=True).start()
            print("▶️ Container Runtime started.")

    def stop(self):
        self.running = False
        print("⏹️ Container Runtime stopped.")

    def run_loop(self):
        while self.running:
            tick_log = self.run_tick()
            self.logs.append(tick_log)

            if self.websocket:
                self.websocket.broadcast({"type": "tick_log", "data": tick_log})
                if summarize_glyphs:
                    summary = summarize_glyphs(self.state_manager.get_current_container().get("cubes", {}))
                    self.websocket.broadcast({"type": "glyph_summary", "data": summary})

            time.sleep(self.tick_interval)

    def run_tick(self):
        container = self.state_manager.get_current_container()
        cubes = container.get("cubes", {})
        tick_log = {"executed": []}

        # Save rewind snapshot
        if self.max_rewind > 0:
            self.rewind_buffer.append({"cubes": cubes.copy()})
            if len(self.rewind_buffer) > self.max_rewind:
                self.rewind_buffer.pop(0)

        for coord_str, data in cubes.items():
            if "glyph" in data:
                x, y, z = map(int, coord_str.split(","))
                print(f"⚙️ Executing glyph at {coord_str}")
                self.executor.execute_glyph_at(x, y, z)
                tick_log["executed"].append(coord_str)

        self.tick_counter += 1
        tick_log["timestamp"] = time.time()
        tick_log["tick"] = self.tick_counter

        # Apply looping logic
        if self.loop_enabled and self.tick_counter % self.loop_interval == 0:
            if self.rewind_buffer:
                rewind_state = self.rewind_buffer[0]
                container["cubes"] = rewind_state["cubes"].copy()
                print("🔄 Container loop: state rewound.")

        # Optional: apply decay logic
        self.apply_decay(container["cubes"])

        return tick_log

    def apply_decay(self, cubes):
        for coord, data in cubes.items():
            if "glyph" in data and data.get("decay", False):
                data["lifespan"] = data.get("lifespan", 10) - 1
                if data["lifespan"] <= 0:
                    print(f"💀 Glyph at {coord} decayed.")
                    data["glyph"] = ""

    def get_logs(self, limit=20):
        return self.logs[-limit:]

    def enable_looping(self, enable=True, interval=50):
        self.loop_enabled = enable
        self.loop_interval = interval

    # ✅ NEW: Timeline playback support
    def get_rewind_state(self, tick_offset: int = -1):
        """Returns the container state at a given offset from latest (-1 = latest, -2 = previous, etc.)"""
        if not self.rewind_buffer:
            return None
        index = tick_offset % len(self.rewind_buffer)
        return self.rewind_buffer[index]["cubes"]

register_dna_switch(__file__)