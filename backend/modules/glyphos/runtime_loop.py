# backend/modules/glyphos/runtime_loop.py

import asyncio
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.memory.memory_bridge import MemoryBridge


class GlyphRuntimeLoop:
    def __init__(self, debug: bool = True):
        self.state_manager = state_manager 
        self.executor = GlyphExecutor(self.state_manager)
        self.seen_glyphs = set()
        self.debug = debug

        container_id = self.state_manager.get_current_container_id() or "default"
        self.bridge = MemoryBridge(container_id)

        self.tick_count = 0
        self.execution_count = 0

    async def tick(self):
        container = self.state_manager.get_current_container()
        if not container or "cubes" not in container:
            return

        self.tick_count = self.state_manager.increment_tick()
        self.bridge.trace_runtime_tick(self.tick_count)

        for coord, data in container["cubes"].items():
            if "glyph" not in data or coord in self.seen_glyphs:
                continue

            try:
                x, y, z = map(int, coord.split(","))
                if self.debug:
                    print(f"⏱️ Tick {self.tick_count}: Executing glyph at {coord}")

                await self.executor.execute_glyph_at(x, y, z)
                self.seen_glyphs.add(coord)
                self.execution_count += 1
            except Exception as e:
                print(f"⚠️ Error executing glyph at {coord}: {e}")

    async def run_loop(self, interval: int = 2):
        print("🔁 Starting Glyph Runtime Loop...")
        while True:
            await self.tick()
            await asyncio.sleep(interval)


if __name__ == "__main__":
    try:
        loop = GlyphRuntimeLoop()
        asyncio.run(loop.run_loop())
    except KeyboardInterrupt:
        print("\n⛔ Runtime loop manually stopped.")