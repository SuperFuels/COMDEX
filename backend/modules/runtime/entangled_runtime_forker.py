import time
from copy import deepcopy
from typing import Dict, Any


class EntangledRuntimeForker:
    """
    Responsible for forking an existing container into two or more superposed execution branches
    based on QGlyph entanglement. Used when ↔ glyphs are detected during runtime.
    """

    def __init__(self, state_manager):
        self.state_manager = state_manager

        # ✅ Compatibility shim for container registries
        # Legacy (pre-F3): .all_containers
        # Modern UCSRuntime: .containers
        if not hasattr(self.state_manager, "all_containers"):
            if hasattr(self.state_manager, "containers"):
                self.state_manager.all_containers = self.state_manager.containers
            else:
                self.state_manager.all_containers = {}

    def fork_container(self, container: Dict[str, Any], coord: str, glyph: str) -> list:
        """
        Creates two entangled versions of the current container to represent superposed paths.
        One path will assume glyph state A:0, the other A:1 (e.g., for [⚛:0 ↔ 1])
        """
        container_id = container.get("id", "unknown")
        timestamp = time.time()

        forks = []

        for idx, branch_value in enumerate(["0", "1"]):
            fork_id = f"{container_id}__qpath_{idx}"
            fork = deepcopy(container)
            fork["id"] = fork_id
            fork["origin"] = container_id
            fork["entangled"] = True
            fork["created_from"] = coord
            fork["glyph"] = glyph
            fork["branch"] = branch_value
            fork["metadata"] = {
                "entangled_from": container_id,
                "trigger_glyph": glyph,
                "fork_time": timestamp,
                "qbranch": branch_value,
                "coord": coord,
            }

            # Modify cube glyph state for each branch (collapse assumption)
            if coord in fork.get("cubes", {}):
                raw = fork["cubes"][coord].get("glyph", "")
                collapsed = self._collapse(raw, branch_value)
                fork["cubes"][coord]["glyph"] = collapsed

            # ✅ Store fork into unified container registry
            self.state_manager.all_containers[fork_id] = fork
            forks.append(fork)

        print(f"🔀 Entangled forks created: {[f['id'] for f in forks]}")
        return forks

    def _collapse(self, glyph: str, branch: str) -> str:
        """Collapse a QGlyph like [⚛:0 ↔ 1] to [⚛:0] or [⚛:1]"""
        if "[" in glyph and "]" in glyph:
            try:
                prefix = glyph.split(":")[0].strip("[")
                return f"[{prefix}:{branch}]"
            except Exception:
                return glyph  # fail-safe fallback
        return glyph