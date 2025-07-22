# glyph_runtime.py

import asyncio
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.hexcore.memory_engine import MemoryEngine


class GlyphRuntime:
    def __init__(self, state_manager: StateManager):
        self.executor = GlyphExecutor(state_manager)
        self.state_manager = state_manager
        self.interval = 1.0  # seconds between scans

    async def tick(self):
        container = self.state_manager.get_current_container()
        container_id = container.get("id", "unknown")
        cubes = container.get("cubes", {})

        tasks = []

        for coord, data in cubes.items():
            glyph = data.get("glyph", "")
            if glyph:
                try:
                    x, y, z = map(int, coord.split(","))
                    print(f"⏱️ Runtime tick found glyph at ({coord}) in container [{container_id}] → Executing")

                    # Log to memory before execution
                    MemoryEngine.store({
                        "type": "glyph_tick",
                        "timestamp": self.state_manager.now_iso(),
                        "container": container_id,
                        "coord": coord,
                        "glyph": glyph,
                        "tags": ["runtime", "tick", "glyph"]
                    })

                    tasks.append(self.executor.execute_glyph_at(x, y, z))  # async
                except Exception as e:
                    print(f"[⚠️] Invalid glyph coordinate {coord}: {e}")

        if tasks:
            await asyncio.gather(*tasks)  # ✅ await them concurrently

    async def run(self, duration_seconds=10):
        print(f"🌀 Starting GlyphRuntime loop for {duration_seconds}s...")
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < duration_seconds:
            await self.tick()
            await asyncio.sleep(self.interval)

        print("✅ GlyphRuntime loop complete.")


# Optional CLI runner
if __name__ == "__main__":
    async def main():
        state_manager = StateManager()
        runtime = GlyphRuntime(state_manager)
        await runtime.run(duration_seconds=10)

    asyncio.run(main())