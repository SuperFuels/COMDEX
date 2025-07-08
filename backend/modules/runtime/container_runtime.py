# container_runtime.py

import time
import threading
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.websocket.websocket_manager import WebSocketManager  # Optional
from backend.modules.dna_chain.dna_switch import register_dna_switch

class ContainerRuntime:
    def __init__(self, state_manager: StateManager, tick_interval: float = 2.0):
        self.state_manager = state_manager
        self.executor = GlyphExecutor(state_manager)
        self.tick_interval = tick_interval
        self.running = False
        self.logs = []
        self.websocket = WebSocketManager()  # Optional WebSocket feedback

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
            self.websocket.broadcast({"type": "tick_log", "data": tick_log})  # Optional
            time.sleep(self.tick_interval)

    def run_tick(self):
        container = self.state_manager.get_current_container()
        cubes = container.get("cubes", {})
        tick_log = {"executed": []}

        for coord_str, data in cubes.items():
            if "glyph" in data:
                x, y, z = map(int, coord_str.split(","))
                print(f"⚙️ Executing glyph at {coord_str}")
                self.executor.execute_glyph_at(x, y, z)
                tick_log["executed"].append(coord_str)

        tick_log["timestamp"] = time.time()
        return tick_log

    def get_logs(self, limit=20):
        return self.logs[-limit:]

register_dna_switch(__file__)