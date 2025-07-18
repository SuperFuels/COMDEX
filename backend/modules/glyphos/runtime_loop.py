# runtime_loop.py

import asyncio
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.memory.memory_bridge import MemoryBridge  # ✅ New import


class GlyphRuntimeLoop:
    def __init__(self):
        self.state_manager = StateManager()
        self.executor = GlyphExecutor(self.state_manager)
        self.seen_glyphs = set()
        container_id = self.state_manager.get_current_container_id() or "default"
        self.bridge = MemoryBridge(container_id)  # ✅ Initialize bridge

    async def tick(self):
        container = self.state_manager.get_current_container()
        if not container or "cubes" not in container:
            return

        tick_number = self.state_manager.increment_tick()
        self.bridge.trace_runtime_tick(tick_number)  # ✅ Log tick trace

        for coord, data in container["cubes"].items():
            if "glyph" not in data:
                continue
            if coord in self.seen_glyphs:
                continue  # Skip already triggered glyphs (optional)

            try:
                x, y, z = map(int, coord.split(","))
                print(f"⏱️ Tick {tick_number}: Executing glyph at {coord}")
                await self.executor.execute_glyph_at(x, y, z)  # ✅ Await async execution
                self.seen_glyphs.add(coord)
            except Exception as e:
                print(f"⚠️ Error executing glyph at {coord}: {e}")

    async def run_loop(self, interval=2):
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