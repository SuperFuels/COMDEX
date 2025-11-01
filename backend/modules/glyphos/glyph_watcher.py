# File: backend/modules/glyphos/glyph_watcher.py

import asyncio
import hashlib
import time
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.hexcore.memory_engine import MEMORY


class GlyphWatcher:
    def __init__(self, state_manager: StateManager, async_loop: asyncio.AbstractEventLoop = None, scan_cooldown: float = 1.0):
        # 🔄 Lazy import to avoid circular dependency
        from backend.modules.glyphos.glyph_executor import GlyphExecutor
        self.executor = GlyphExecutor(state_manager)
        self.state_manager = state_manager
        self.async_loop = async_loop or asyncio.get_event_loop()
        self.previous_hash = None
        self.previous_grid = {}
        self.last_scan_time = 0
        self.scan_cooldown = scan_cooldown  # seconds

    def scan_for_bytecode(self):
        """
        Scan the current container for glyphs with encoded bytecode.
        Execute or defer based on prefix.
        """
        if time.time() - self.last_scan_time < self.scan_cooldown:
            return  # ⏱️ Throttle to avoid excessive scanning

        self.last_scan_time = time.time()
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
                    self.handle_bytecode(glyph, x, y, z, container.get("id"))
                except ValueError:
                    print(f"❌ Invalid coordinate format: {coord}")

    def handle_bytecode(self, glyph: str, x: int, y: int, z: int, container_id: str):
        """
        Handle decoding and execution or deferral of bytecode glyphs.
        """
        timestamp = time.time()
        if glyph.startswith("⎇:"):
            print(f"🧬 Executing decoded glyph at ({x},{y},{z})")
            MEMORY.store({
                "timestamp": timestamp,
                "role": "system",
                "type": "bytecode_exec",
                "container_id": container_id,
                "location": (x, y, z),
                "glyph": glyph
            })
            coro = self.executor.execute_glyph_at(x, y, z)
            asyncio.run_coroutine_threadsafe(coro, self.async_loop)

        elif glyph.startswith("⧉:"):
            print(f"📡 Deferred glyph at ({x},{y},{z}) -> Routing placeholder")
            MEMORY.store({
                "timestamp": timestamp,
                "role": "system",
                "type": "bytecode_deferred",
                "container_id": container_id,
                "location": (x, y, z),
                "glyph": glyph,
                "status": "pending_remote_routing"
            })
            # 🔌 Future implementation: route_to_remote_handler(glyph, location)

    def watch_microgrid(self, cycle_id: str = None):
        """
        Watch the current container's microgrid and log glyph state changes.
        """
        container = self.state_manager.get_current_container()
        if not container:
            print("⚠️ No container loaded. Cannot scan microgrid.")
            return

        microgrid = container.get("microgrid", {})
        current_hash = self._hash_grid(microgrid)

        log_entry = {
            "timestamp": time.time(),
            "role": "system",
            "container_id": container.get("id"),
        }

        if cycle_id:
            log_entry["cycle_id"] = cycle_id

        if self.previous_hash and current_hash != self.previous_hash:
            diffs = self._detect_changes(self.previous_grid, microgrid)
            if diffs:
                log_entry.update({
                    "type": "mutation_detected",
                    "content": f"🧬 Glyph mutation(s) detected in container.",
                    "data": diffs
                })
                MEMORY.store(log_entry)
        else:
            log_entry.update({
                "type": "glyph_scan",
                "content": f"🧠 Glyph grid scanned for container.",
                "data": microgrid
            })
            MEMORY.store(log_entry)

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