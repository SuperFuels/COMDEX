import hashlib
from backend.modules.hexcore.memory_engine import MEMORY

class GlyphWatcher:
    def __init__(self):
        self.previous_hash = None
        self.previous_grid = {}

    def watch_container(self, container: dict):
        """Scan a container's microgrid and log glyph states."""
        microgrid = container.get("microgrid", {})
        current_hash = self._hash_grid(microgrid)

        if self.previous_hash and current_hash != self.previous_hash:
            diffs = self._detect_changes(self.previous_grid, microgrid)
            if diffs:
                MEMORY.store({
                    "role": "system",
                    "type": "mutation_detected",
                    "content": f"�� Glyph mutation(s) detected in container: {container.get('id')}",
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
