# glyph_runtime.py
# Runtime loop for executing glyphs within active containers.
# Adds Codex SQI aggregation, tick profiling, and runtime performance logs.

import asyncio
import time
from statistics import mean

from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.hexcore.memory_engine import MemoryEngine


def _safe_timestamp(state_manager: StateManager) -> str:
    """Returns ISO timestamp via StateManager if available, else fallback."""
    try:
        if hasattr(state_manager, "now_iso"):
            return state_manager.now_iso()
    except Exception:
        pass
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class GlyphRuntime:
    def __init__(self, state_manager: StateManager):
        self.executor = GlyphExecutor(state_manager)
        self.state_manager = state_manager
        self.memory_engine = MemoryEngine()
        self.interval = 1.0  # seconds between scans

    async def tick(self):
        start_tick = time.time()
        container = self.state_manager.get_current_container()

        # --- Safety guard: handle missing container gracefully ---
        if not container:
            print("⚠️ [GlyphRuntime] No active container found - using fallback stub.")
            container = {"id": "default_stub", "cubes": {}}

        container_id = container.get("id", "unknown")
        cubes = container.get("cubes", {}) or {}

        print(f"\n🌀 [RuntimeTick] Beginning tick for container '{container_id}' "
              f"with {len(cubes)} cubes...")

        tasks = []

        for coord, data in cubes.items():
            glyph = data.get("glyph", "")
            if glyph:
                try:
                    x, y, z = map(int, coord.split(","))
                    print(f"⏱️ Runtime tick found glyph at ({coord}) in container [{container_id}] -> Executing")

                    # ✅ Structured memory log
                    self.memory_engine.store({
                        "label": "glyph_tick",
                        "content": {
                            "timestamp": _safe_timestamp(self.state_manager),
                            "container": container_id,
                            "coord": coord,
                            "glyph": glyph,
                            "tags": ["runtime", "tick", "glyph"]
                        }
                    })

                    # Run glyph asynchronously
                    task = asyncio.create_task(self.executor.execute_glyph_at(x, y, z))
                    tasks.append(task)

                except Exception as e:
                    print(f"[⚠️] Invalid glyph coordinate {coord}: {e}")

        # Execute all glyph tasks concurrently
        if tasks:
            await asyncio.gather(*tasks)

        elapsed_tick = time.time() - start_tick
        print(f"✅ [RuntimeTick] Completed container '{container_id}' in {elapsed_tick:.3f}s")

        # === SQI Feedback Aggregation ===
        try:
            from backend.modules.codex.codex_metrics import CodexMetrics
            metrics = CodexMetrics()
            recent_scores = metrics.get_recent_scores(limit=10)
            if recent_scores:
                avg_sqi = mean(recent_scores)
                print(f"[📈 SQI Aggregate] Average SQI: {avg_sqi:.3f} over {len(recent_scores)} samples")

                self.memory_engine.store({
                    "label": "runtime_sqi_tick",
                    "content": {
                        "timestamp": _safe_timestamp(self.state_manager),
                        "container": container_id,
                        "avg_sqi": avg_sqi,
                        "sample_count": len(recent_scores)
                    }
                })
        except Exception:
            # Skip if metrics unavailable
            pass

        # === Store tick summary ===
        self.memory_engine.store({
            "label": "runtime_tick_summary",
            "content": {
                "timestamp": _safe_timestamp(self.state_manager),
                "container": container_id,
                "duration": elapsed_tick,
                "glyph_count": len(tasks)
            }
        })

    async def run(self, duration_seconds=10):
        print(f"🧩 Starting GlyphRuntime loop for {duration_seconds}s...")
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < duration_seconds:
            await self.tick()
            await asyncio.sleep(self.interval)

        print("✅ GlyphRuntime loop complete.")


# Optional CLI runner
if __name__ == "__main__":
    import asyncio
    from backend.modules.consciousness.state_manager import state_manager

    async def main():
        runtime = GlyphRuntime(state_manager)

        # --- ✅ Insert mock container here ---
        runtime.state_manager.set_current_container({
            "id": "mock_container",
            "cubes": {
                "0,0,0": {"glyph": "⊕"},
                "1,0,0": {"glyph": "∇"},
                "0,1,0": {"glyph": "↔"},
            },
        })
        # -------------------------------------

        await runtime.run(duration_seconds=10)

    asyncio.run(main())