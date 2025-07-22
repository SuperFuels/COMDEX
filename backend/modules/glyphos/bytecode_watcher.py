# backend/modules/glyphos/bytecode_watcher.py

import time
import threading
from typing import Callable, Dict, Union
from backend.modules.dimensions.dc_handler import load_dimension
from backend.modules.glyphos.glyph_parser import parse_glyph
from backend.modules.glyphos.microgrid_index import cube_to_coord

WATCH_INTERVAL = 5  # seconds

class BytecodeWatcher:
    def __init__(self, dc_path: str, on_glyph_detected: Callable):
        self.dc_path = dc_path
        self.on_glyph_detected = on_glyph_detected
        self._seen = set()
        self._running = False
        self._thread = None

    def _watch_loop(self):
        print(f"[👁️] Bytecode watcher started on {self.dc_path}")
        while self._running:
            try:
                dimension = load_dimension(self.dc_path)
                cubes = dimension.get("cubes", {})

                # Support both list and dict styles
                if isinstance(cubes, list):
                    items = enumerate(cubes)
                else:
                    items = cubes.items()

                for coord_key, cube in items:
                    try:
                        coord = cube_to_coord(cube) if isinstance(cube, dict) else str(coord_key)
                        bytecode = cube.get("bytecode")
                        if bytecode and coord not in self._seen:
                            glyph = parse_glyph(bytecode)
                            self.on_glyph_detected(glyph, coord)
                            self._seen.add(coord)
                    except Exception as e:
                        print(f"[⚠️] Skipping invalid glyph at {coord_key}: {e}")

                print(f"[🔍] Scanned {len(cubes)} cubes in {self.dc_path}")
            except Exception as e:
                print(f"[❌] Watcher error: {e}")
            time.sleep(WATCH_INTERVAL)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)

    def reset_seen(self):
        self._seen.clear()
        print("[♻️] Seen glyphs reset")


# 🔁 Example usage for test/dev
if __name__ == "__main__":
    def print_glyph(glyph, coord):
        print(f"[🧬] New glyph detected at {coord}: {glyph}")

    watcher = BytecodeWatcher("backend/modules/dimensions/containers/test.dc", print_glyph)
    watcher.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()