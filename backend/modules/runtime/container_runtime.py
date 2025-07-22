# File: backend/modules/runtime/container_runtime.py

import time
import threading
import asyncio
from typing import Dict, Any, Optional
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.websocket_manager import WebSocketManager
from backend.modules.glyphos.glyph_watcher import GlyphWatcher

# ✅ Optional glyph summarizer
try:
    from backend.modules.glyphos.glyph_summary import summarize_glyphs
except ImportError:
    summarize_glyphs = None


class ContainerRuntime:
    def __init__(self, state_manager: StateManager, tick_interval: float = 2.0):
        self.state_manager = state_manager
        self.executor = GlyphExecutor(state_manager)
        self.glyph_watcher = GlyphWatcher(state_manager)
        self.tick_interval = tick_interval
        self.running = False
        self.logs: list[Dict[str, Any]] = []
        self.websocket = WebSocketManager()
        self.tick_counter = 0
        self.loop_enabled = False
        self.loop_interval = 50
        self.rewind_buffer: list[Dict[str, Any]] = []
        self.max_rewind = 5

        # ✅ Async event loop in background thread
        self.async_loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._start_event_loop, daemon=True)
        self.loop_thread.start()

    def _start_event_loop(self):
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()

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

                # ✅ NEW: Send dimension_tick event
                self.websocket.broadcast({
                    "type": "dimension_tick",
                    "data": {
                        "tick": self.tick_counter,
                        "timestamp": time.time()
                    }
                })

                if summarize_glyphs:
                    summary = summarize_glyphs(self.state_manager.get_current_container().get("cubes", {}))
                    self.websocket.broadcast({"type": "glyph_summary", "data": summary})

            time.sleep(self.tick_interval)

    def run_tick(self) -> Dict[str, Any]:
        container = self.state_manager.get_current_container()
        cubes = container.get("cubes", {})
        tick_log = {"executed": []}

        # Save rewind snapshot
        if self.max_rewind > 0:
            self.rewind_buffer.append({"cubes": cubes.copy()})
            if len(self.rewind_buffer) > self.max_rewind:
                self.rewind_buffer.pop(0)

        # 🔍 Scan for ⎇: or ⧉: bytecode glyphs
        self.glyph_watcher.scan_for_bytecode()

        for coord_str, data in cubes.items():
            if "glyph" in data and data["glyph"]:
                try:
                    x, y, z = map(int, coord_str.split(","))
                    print(f"⚙️ Executing glyph at {coord_str}")
                    coro = self.executor.execute_glyph_at(x, y, z)
                    asyncio.run_coroutine_threadsafe(coro, self.async_loop)
                    tick_log["executed"].append(coord_str)
                except Exception as e:
                    print(f"❌ Failed to execute glyph at {coord_str}: {e}")

        self.tick_counter += 1
        tick_log["timestamp"] = time.time()
        tick_log["tick"] = self.tick_counter

        # Looping logic
        if self.loop_enabled and self.tick_counter % self.loop_interval == 0:
            if self.rewind_buffer:
                rewind_state = self.rewind_buffer[0]
                container["cubes"] = rewind_state["cubes"].copy()
                print("🔄 Container loop: state rewound.")

        self.apply_decay(container["cubes"])
        return tick_log

    def apply_decay(self, cubes: Dict[str, Dict[str, Any]]):
        for coord, data in cubes.items():
            if "glyph" in data and data.get("decay", False):
                data["lifespan"] = data.get("lifespan", 10) - 1
                if data["lifespan"] <= 0:
                    print(f"💀 Glyph at {coord} decayed.")
                    data["glyph"] = ""

    def get_logs(self, limit: int = 20) -> list[Dict[str, Any]]:
        return self.logs[-limit:]

    def enable_looping(self, enable: bool = True, interval: int = 50):
        self.loop_enabled = enable
        self.loop_interval = interval

    # ✅ Timeline playback support
    def get_rewind_state(self, tick_offset: int = -1) -> Optional[Dict[str, Any]]:
        if not self.rewind_buffer:
            return None
        index = tick_offset % len(self.rewind_buffer)
        return self.rewind_buffer[index]["cubes"]


# ✅ External getter used by FastAPI route or runtime script
def get_container_runtime(tick_interval: float = 2.0) -> ContainerRuntime:
    state_manager = StateManager()
    return ContainerRuntime(state_manager, tick_interval=tick_interval)