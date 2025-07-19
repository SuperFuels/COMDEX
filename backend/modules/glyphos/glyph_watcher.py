# File: backend/modules/glyphos/glyph_watcher.py

import asyncio
import hashlib
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.hexcore.memory_engine import MEMORY


class GlyphWatcher:
    def __init__(self, state_manager: StateManager, async_loop: asyncio.AbstractEventLoop = None):
        self.executor = GlyphExecutor(state_manager)
        self.state_manager = state_manager
        self.async_loop = async_loop or asyncio.get_event_loop()
        self.previous_hash = None
        self.previous_grid = {}

    def scan_for_bytecode(self):
        """
        Scan the current container for glyphs with encoded bytecode.
        Execute or defer based on prefix.
        """
        container = self.state_manager.get_current_container()
        if not container:
            print("⚠️ No container loaded. Cannot scan for glyphs.")
            return

        cubes = container.get("cubes", {})
        if not cubes:
            print("⚠️ Container has no cubes.")
            return

        for coord, data in cubes.items():
            glyph = data.get("glyph", "")
            if glyph.startswith("⎇:") or glyph.startswith("⧉:"):
                try:
                    x, y, z = map(int, coord.split(","))
                    print(f"📦 Detected bytecode glyph at {coord}: {glyph}")
                    self.handle_bytecode(glyph, x, y, z)
                except ValueError:
                    print(f"❌ Invalid coordinate format: {coord}")

    def handle_bytecode(self, glyph: str, x: int, y: int, z: int):
        """
        Handle decoding and execution or deferral of bytecode glyphs.
        """
        if glyph.startswith("⎇:"):
            print(f"🧬 Executing decoded glyph at ({x},{y},{z})")
            coro = self.executor.execute_glyph_at(x, y, z)
            asyncio.run_coroutine_threadsafe(coro, self.async_loop)

        elif glyph.startswith("⧉:"):
            print(f"📡 Deferred glyph at ({x},{y},{z}) → Remote logic not yet implemented.")
            # TODO: Future support for remote execution or glyph routing.

    def watch_microgrid(self):
        """
        Watch the current container's microgrid and log glyph state changes.
        """
        container = self.state_manager.get_current_container()
        if not container:
            print("⚠️ No container loaded. Cannot scan microgrid.")
            return

        microgrid = container.get("microgrid", {})
        current_hash = self._hash_grid(microgrid)

        if self.previous_hash and current_hash != self.previous_hash:
            diffs = self._detect_changes(self.previous_grid, microgrid)
            if diffs:
                MEMORY.store({
                    "role": "system",
                    "type": "mutation_detected",
                    "content": f"🧬 Glyph mutation(s) detected in container: {container.get('id')}",
                    "data": diffs
                })
        else:
            MEMORY.store({
                "role": "system",
                "type": "glyph_scan",
                "content": f"🧠 Glyph grid scanned for container: {container.get('id')}",
                "data": microgrid
            })

        self.previous_hash = current_hash
        self.previous_grid = microgrid

    def _hash_grid(self, microgrid: dict):
        """Create a hash for comparison across cycles."""
        sorted_items = sorted((str(k), str(v)) for k, v in microgrid.items())
        hash_input = "".join([f"{k}:{v}" for k, v in sorted_items])
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def _detect_changes(self, prev: dict, curr: dict):
        """Detect glyph-level changes between previous and current grid."""
        diffs = []
        for pos, glyph in curr.items():
            if pos not in prev:
                diffs.append({"position": pos, "change": "added", "glyph": glyph})
            elif glyph != prev[pos]:
                diffs.append({"position": pos, "change": "modified", "from": prev[pos], "to": glyph})
        for pos in prev:
            if pos not in curr:
                diffs.append({"position": pos, "change": "removed", "glyph": prev[pos]})
        return diffs