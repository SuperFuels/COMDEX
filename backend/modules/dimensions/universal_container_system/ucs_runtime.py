"""
🧮 UCS Runtime
-----------------------------------------------------
Handles:
    • Container loading/execution
    • GHXVisualizer integration
    • SQI runtime + Pi GPIO event output
    • SoulLaw enforcement
    • Geometry registration + trigger map events
    • Legacy container_runtime API compatibility
"""

import json
import os
import time
from typing import Dict, Any
from typing import Dict, Any, List, Optional
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCSGeometryLoader
from backend.modules.dimensions.universal_container_system.ucs_soullaw import SoulLawEnforcer
from backend.modules.dimensions.universal_container_system.ucs_trigger_map import UCSTriggerMap

# Stub GHXVisualizer (frontend-only)
class GHXVisualizer:
    def add_container(self, container): 
        print(f"[GHXVisualizer] (stub) Added container {container.get('name')}")
    def highlight(self, name): 
        print(f"[GHXVisualizer] (stub) Highlighting {name}")
    # NEW: quiet the AttributeError; callers expect this hook
    def log_event(self, *args, **kwargs):
        # keep as no-op or uncomment for visibility
        # print(f"[GHXVisualizer] (stub) log_event {args} {kwargs}")
        pass

class UCSRuntime:
    def __init__(self):
        self.containers: Dict[str, Dict[str, Any]] = {}

        # ✅ SQIRuntime alias defined post-class to avoid circular import
        self.sqi = None  
        self.active_container_name = None  # <-- NEW: track active container
        self.visualizer = GHXVisualizer()
        self.geometry_loader = UCSGeometryLoader()
        self.soul_law = SoulLawEnforcer()
        self.trigger_map = UCSTriggerMap()
        self.atom_index: Dict[str, Any] = {}

    def load_containers(self):
        """
        Load all UCS containers and build the atom index.
        """
        # existing container load code...
        for cid, container in self.containers.items():
            for atom in container.get("atoms", []):
                self.atom_index[atom["id"]] = atom

    # ---------------------------------------------------------
    # 🔑 Load and Manage Containers
    # ---------------------------------------------------------
    def load_container(self, path: str) -> str:
        """Load a .dc.json container into UCS runtime."""
        with open(path, 'r') as f:
            container_data = json.load(f)

        name = container_data.get("name") or os.path.basename(path).replace(".dc.json", "")
        self.containers[name] = container_data
        self.active_container_name = name  # <-- mark active on load

        # Geometry + Visualization
        self.geometry_loader.register_geometry(name, container_data.get("geometry", "default"))
        self.visualizer.add_container(container_data)

        # NEW: ensure container is registered for atoms, then index any atoms present
        self.register_container(name, self.containers[name])
        for atom in self.containers[name].get("atoms", []):
            try:
                self.register_atom(name, atom)
            except Exception as e:
                print(f"⚠️  Skipped atom without valid id in {name}: {e}")

        # NEW: ensure container is registered for atoms, then index any atoms present
        self.register_container(name, self.containers[name])
        atoms_data = self.containers[name].get("atoms", [])

        # If atoms are given as a list, wrap them into dict form
        if isinstance(atoms_data, list):
            for atom in atoms_data:
                try:
                    self.register_atom(name, atom)
                except Exception as e:
                    print(f"⚠️  Skipped atom without valid id in {name}: {e}")
        elif isinstance(atoms_data, dict):
            for atom_id, atom in atoms_data.items():
                try:
                    self.register_atom(name, atom)
                except Exception as e:
                    print(f"⚠️  Skipped atom {atom_id} in {name}: {e}")

        print(f"✅ Loaded container: {name}")
        return name

    def choose_route(self, goal: Dict[str, Any], k: int = 3) -> Dict[str, Any]:
        """Select a route of atoms for achieving a goal."""
        atom_ids = self.compose_path(goal, k=k)
        return {
            "goal": goal,
            "atoms": atom_ids,
            "plan": [{"atom_id": a, "mode": "sequential"} for a in atom_ids]
        }
        
    def save_container(self, name: str, data: Dict[str, Any]):
        """Save container state into runtime memory."""
        self.containers[name] = data
        self.active_container_name = name  # <-- mark active on save

    def get_container(self, name: str) -> Dict[str, Any]:
        """Retrieve container state."""
        return self.containers.get(name, {})

    # NEW: API shim for modules that expect this
    def get_active_container(self) -> Dict[str, Any]:
        """Best-effort active container for modules that expect this API."""
        if self.active_container_name and self.active_container_name in self.containers:
            return self.containers[self.active_container_name]
        if self.containers:
            # fall back to first/only container
            return next(iter(self.containers.values()))
        return {"id": "ucs_ephemeral", "glyph_grid": []}

     # ---------------------------------------------------------
    # 🧩 Atom registration + path composition (NEW)
    # ---------------------------------------------------------
    def register_container(self, name: str, payload: Dict[str, Any]) -> None:
        """
        Ensure a container record exists and is ready to host atoms.
        Safe to call multiple times; no-ops after first.
        """
        self.containers.setdefault(name, payload)
        self.containers[name].setdefault("atoms", {})

    def register_atom(self, container_name: str, atom: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a single atom dict under a container and index it globally.
        Expected keys include: id, caps, tags, nodes, requires, produces, viz...
        """
        if "id" not in atom:
            raise ValueError("Atom missing required field 'id'")

        self.register_container(container_name, self.containers.get(container_name, {}))
        self.containers[container_name]["atoms"][atom["id"]] = atom

        # store flat index for route planning
        self.atom_index[atom["id"]] = (container_name, atom)
        return atom

    def get_atoms(self, selector: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query atoms by simple filters:
          selector = {"caps": [...], "tags": [...], "nodes": [...]}
        Any provided filter acts as an OR within the field and AND across fields.
        """
        if not self.atom_index:
            return []

        caps_req  = set((selector or {}).get("caps", []))
        tags_req  = set((selector or {}).get("tags", []))
        nodes_req = set((selector or {}).get("nodes", []))

        results: List[Dict[str, Any]] = []
        for _, atom in self.atom_index.values():
            if caps_req  and not caps_req.intersection(atom.get("caps", [])):   continue
            if tags_req  and not tags_req.intersection(atom.get("tags", [])):   continue
            if nodes_req and not nodes_req.intersection(atom.get("nodes", [])): continue
            results.append(atom)
        return results

    def compose_path(self, goal: Dict[str, Any], k: int = 3) -> List[str]:
        """
        Greedy scorer for now (safe default). Returns top-k atom IDs.
        goal example:
          {"caps":["lean.replay","proof.graph"], "tags":["math"], "nodes":["logic_core"]}
        Score = 2*cap_overlap + 1*node_overlap + 0.5*tag_overlap
        """
        if not self.atom_index:
            return []

        want_caps  = set(goal.get("caps", []))
        want_tags  = set(goal.get("tags", []))
        want_nodes = set(goal.get("nodes", []))

        scored: List[tuple[float, str]] = []
        for _, atom in self.atom_index.values():
            score = 0.0
            score += 2.0 * len(want_caps.intersection(set(atom.get("caps", []))))
            score += 1.0 * len(want_nodes.intersection(set(atom.get("nodes", []))))
            score += 0.5 * len(want_tags.intersection(set(atom.get("tags", []))))
            scored.append((score, atom["id"]))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [aid for s, aid in scored[:k] if s > 0.0]

    def debug_state(self) -> Dict[str, Any]:
        return {
            "containers": list(self.containers.keys()),
            "active_container": self.active_container_name,
            "atom_index_count": len(self.atom_index),
            "atom_ids": list(self.atom_index.keys()),
        }

    # ---------------------------------------------------------
    # 🚀 Runtime Execution
    # ---------------------------------------------------------
    def run_container(self, name: str):
        """Execute a container's symbolic runtime."""
        if name not in self.containers:
            raise ValueError(f"Container '{name}' not loaded.")
        container = self.containers[name]
        print(f"🚀 Running container: {name}")

        # 🛡 SoulLaw enforcement
        self.soul_law.validate_access(container)

        # 🔥 Trigger glyph-based events
        for glyph in container.get("glyphs", []):
            if glyph in self.trigger_map.map:
                event = self.trigger_map.map[glyph]
                self.emit_event(event, container)

        # 🎨 GHX Visualization highlight
        self.visualizer.highlight(name)
        self.active_container_name = name  # <-- mark active on highlight

    def run_all(self):
        """Run all loaded containers sequentially (basic orchestration)."""
        for name in self.containers.keys():
            self.run_container(name)
            time.sleep(0.5)  # pacing for visual clarity

    # ---------------------------------------------------------
    # ⚡ Event & SQI Integration
    # ---------------------------------------------------------
    def emit_event(self, event_name: str, container: dict):
        """Emit an event into SQI runtime (GPIO-capable for Pi testbench)."""
        print(f"⚡ Emitting event: {event_name} from {container['name']}")
        if self.sqi:
            self.sqi.emit(event_name, payload={"container": container})

    # ---------------------------------------------------------
    # 🧩 Expansion / Collapse (Legacy API Compatibility)
    # ---------------------------------------------------------
    def expand_container(self, name: str):
        """Expand container (legacy alias)."""
        c = self.get_container(name)
        c["state"] = "expanded"
        self.save_container(name, c)
        return c

    def collapse_container(self, name: str):
        """Collapse container (legacy alias)."""
        c = self.get_container(name)
        c["state"] = "collapsed"
        self.save_container(name, c)
        return c

    def load_dc_container(self, name: str):
        """Alias for legacy container loading (returns runtime memory container)."""
        return self.get_container(name)

    def embed_glyph_block_into_container(self, name: str, glyph_block: Any):
        """Embed glyph block (legacy alias for Codex injection)."""
        c = self.get_container(name)
        c.setdefault("glyphs", []).append(glyph_block)
        self.save_container(name, c)

    def choose_route(self, goal: Dict[str, Any], k: int = 3) -> Dict[str, Any]:
        atom_ids = self.compose_path(goal, k=k)
        return {
            "goal": goal,
            "atoms": atom_ids,
            "plan": [{"atom_id": a, "mode": "sequential"} for a in atom_ids]
        }

# ---------------------------------------------------------
# ✅ Singleton + Legacy Aliases
# ---------------------------------------------------------
ucs_runtime = UCSRuntime()

# ✅ Define SQIRuntime alias after UCSRuntime definition to avoid circular import
SQIRuntime = UCSRuntime  
ucs_runtime.sqi = SQIRuntime()

# Legacy compatibility shims
load_dc_container = ucs_runtime.load_dc_container
expand_container = ucs_runtime.expand_container
collapse_container = ucs_runtime.collapse_container
embed_glyph_block_into_container = ucs_runtime.embed_glyph_block_into_container

__all__ = [
    "UCSRuntime",
    "ucs_runtime",
    "load_dc_container",
    "expand_container",
    "collapse_container",
    "embed_glyph_block_into_container",
]

# ---------------------------------------------------------
# ✅ Singleton + Legacy Aliases
# ---------------------------------------------------------
ucs_runtime = UCSRuntime()

# ✅ Define SQIRuntime alias after UCSRuntime definition to avoid circular import
SQIRuntime = UCSRuntime  
ucs_runtime.sqi = SQIRuntime()

# Legacy compatibility shims
load_dc_container = ucs_runtime.load_dc_container
expand_container = ucs_runtime.expand_container
collapse_container = ucs_runtime.collapse_container
embed_glyph_block_into_container = ucs_runtime.embed_glyph_block_into_container

# ✅ NEW: Provide accessor for imports expecting get_ucs_runtime()
def get_ucs_runtime() -> UCSRuntime:
    """Return the global UCS runtime singleton (for vault + hyperdrive)."""
    return ucs_runtime

__all__ = [
    "UCSRuntime",
    "ucs_runtime",
    "get_ucs_runtime",  # ✅ Exported now
    "load_dc_container",
    "expand_container",
    "collapse_container",
    "embed_glyph_block_into_container",
]