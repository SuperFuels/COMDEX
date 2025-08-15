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

from __future__ import annotations

import os
import json
import inspect
from typing import Dict, Any, List, Optional
from json import JSONDecodeError

# Core subsystems
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import (
    UCSGeometryLoader,
)
from backend.modules.dimensions.universal_container_system.ucs_soullaw import (
    SoulLawEnforcer,
)
from backend.modules.dimensions.universal_container_system.ucs_trigger_map import (
    UCSTriggerMap,
)

# Global registry helpers
from backend.modules.dna_chain.dna_address_lookup import (
    register_container_address,
    unregister_container as registry_unregister_container,
    link_wormhole,
    resolve_by_address,
    list_addresses as registry_list_addresses,
)

DEFAULT_HUB_ID = "ucs_hub"
DEFAULT_HUB_ADDRESS = "ucs://root/hub#container"


# ─────────────────────────────────────────────────────────────────────────────
# Small visualizer stub (front-end binds a real one)
# ─────────────────────────────────────────────────────────────────────────────
class GHXVisualizer:
    def add_container(self, container: Dict[str, Any]) -> None:
        print(
            f"[GHXVisualizer] (stub) Added container "
            f"{container.get('name') or container.get('id')}"
        )

    def highlight(self, name: str) -> None:
        print(f"[GHXVisualizer] (stub) Highlighting {name}")

    def log_event(self, *args, **kwargs) -> None:  # no-op; avoid AttributeErrors
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (module-level)
# ─────────────────────────────────────────────────────────────────────────────
def _as_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _mk_atom_dict(atom_like):
    """
    Accepts:
      - "physics_core"
      - {"id":"physics_core", "type":"dc", "labels":[...], "meta":{...}}
    Returns canonical dict: {"id": str, "type": "dc", "labels": [], "meta": {}}
    """
    if isinstance(atom_like, dict):
        aid = atom_like.get("id") or atom_like.get("name")
        if not isinstance(aid, str) or not aid.strip():
            raise ValueError("Atom entry missing string 'id'")
        return {
            "id": aid,
            "type": atom_like.get("type") or "dc",
            "labels": atom_like.get("labels") or [],
            "meta": atom_like.get("meta") or {},
        }
    if isinstance(atom_like, str):
        return {"id": atom_like, "type": "dc", "labels": [], "meta": {}}
    raise TypeError(f"Unsupported atom entry type: {type(atom_like).__name__}")


def _normalize_atoms(obj: dict) -> List[dict]:
    """
    Accepts:
      - container with 'atoms' as list[str|dict]
      - or a single atom file (type == 'atom')

    Returns list[dict] with at least: id, type, caps, nodes, labels, meta
    """
    atoms: List[dict] = []

    # Single-atom file
    if obj.get("type") == "atom":
        a = dict(obj)  # shallow copy
        a.setdefault("labels", [])
        a.setdefault("meta", {})
        a.setdefault("caps", _as_list(a.get("caps") or a.get("meta", {}).get("caps")))
        a.setdefault("nodes", _as_list(a.get("nodes") or a.get("meta", {}).get("nodes")))
        if not a.get("id"):
            raise ValueError("Atom missing 'id'")
        atoms.append(a)
        return atoms

    # Container with atoms[]
    raw = obj.get("atoms") or []
    if not isinstance(raw, list):
        raise ValueError("Container 'atoms' must be a list")

    for entry in raw:
        if isinstance(entry, str):
            atoms.append(
                {
                    "id": entry,
                    "type": "dc",
                    "labels": [],
                    "meta": {},
                    "caps": [],
                    "nodes": [],
                }
            )
        elif isinstance(entry, dict):
            d = dict(entry)
            d.setdefault("type", "dc")
            d.setdefault("labels", [])
            d.setdefault("meta", {})
            # lift caps/nodes from meta if absent
            if "caps" not in d and isinstance(d["meta"].get("caps"), list):
                d["caps"] = d["meta"]["caps"]
            else:
                d.setdefault("caps", [])
            if "nodes" not in d and isinstance(d["meta"].get("nodes"), list):
                d["nodes"] = d["meta"]["nodes"]
            else:
                d.setdefault("nodes", [])
            if not d.get("id"):
                raise ValueError("Atom entry missing 'id'")
            atoms.append(d)
        else:
            raise ValueError(f"Unsupported atom entry: {type(entry).__name__}")
    return atoms


# ─────────────────────────────────────────────────────────────────────────────
# UCS Runtime (MODULE-LEVEL, not nested in GHXVisualizer)
# ─────────────────────────────────────────────────────────────────────────────
class UCSRuntime:
    def __init__(self) -> None:
        self.containers: Dict[str, Dict[str, Any]] = {}
        self.atom_index: Dict[str, Any] = {}
        self.address_index: Dict[str, str] = {}

        # Optional runtime hooks
        self.sqi = None
        self.visualizer = GHXVisualizer()
        self.geometry_loader = UCSGeometryLoader()
        self.soul_law = SoulLawEnforcer()
        self.trigger_map = UCSTriggerMap()
        self._ghx_registered: set[str] = set()

        self.active_container_name: Optional[str] = None

        # Ensure a minimal hub exists and is registered once
        if DEFAULT_HUB_ID not in self.containers:
            hub = {
                "id": DEFAULT_HUB_ID,
                "type": "container",
                "meta": {
                    "address": DEFAULT_HUB_ADDRESS,
                    "tags": ["hub"],
                    "nodes": ["root"],
                },
                "wormholes": [],
            }
            self.containers[DEFAULT_HUB_ID] = hub
            self.address_index[DEFAULT_HUB_ADDRESS] = DEFAULT_HUB_ID
            try:
                register_container_address(
                    DEFAULT_HUB_ID,
                    DEFAULT_HUB_ADDRESS,
                    meta=hub["meta"],
                    kind="container",
                )
            except Exception:
                pass

    def _ghx_register_once(self, cid: str, name: Optional[str] = None) -> None:
        if cid in self._ghx_registered:
            return
        try:
            if getattr(self, "visualizer", None):
                self.visualizer.add_container({"id": cid, "name": name or cid})
        except Exception:
            pass
        else:
            self._ghx_registered.add(cid)

    # ─────────────────────────────────────────────────────────────────────────
    # Address + wormhole stamping (idempotent)
    # ─────────────────────────────────────────────────────────────────────────
    def _ensure_address_and_wormhole(self, container_id: str, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return

        # meta: always a dict
        meta = data.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            data["meta"] = meta

        ctype = data.get("type", "container")

        # 1) Address
        addr = meta.get("address")
        if not isinstance(addr, str) or not addr.strip():
            addr = f"ucs://local/{container_id}#{ctype}"
            meta["address"] = addr

        # 2) Wormhole list must be a list
        wormholes = data.get("wormholes")
        if not isinstance(wormholes, list):
            wormholes = []
            data["wormholes"] = wormholes

        if DEFAULT_HUB_ID not in wormholes and container_id != DEFAULT_HUB_ID:
            wormholes.append(DEFAULT_HUB_ID)
            # Try to mirror globally, but never fail load if registry is quirky
            try:
                link_wormhole(container_id, DEFAULT_HUB_ID, meta={"reason": "auto_hub"})
            except Exception as e:
                print(f"[UCS] link_wormhole({container_id}->{DEFAULT_HUB_ID}) failed: {e!r}")

        # 3) Local fast index
        self.address_index[addr] = container_id

        # 4) Global registry write (guarded)
        try:
            register_container_address(container_id, addr, meta=meta, kind=ctype)
        except Exception as e:
            print(f"[UCS] register_container_address({container_id}, {addr}) failed: {e!r}")
    
    from typing import Any, Dict, Iterable, Optional

    def _as_list(v: Any) -> list:
        if v is None:
            return []
        if isinstance(v, (list, tuple, set)):
            return list(v)
        return [v]

# --- put these inside class UCSRuntime -------------------------------------

    def register_atom(self, *args, **kwargs) -> str:
        """
        Canonical + back-compat shim.

        Preferred:  register_atom(container_id: str, atom: dict) -> id
        Legacy A:   register_atom(atom_dict) -> id
        Legacy B:   register_atom(atom_id, payload_dict) -> id

        Also:
        - Stores atom under self.containers[container_id]["atoms"][id] (if container_id known)
        - Indexes by atom_id in self.atom_index
        - Maintains self.address_index and best-effort global address registration
        """
        container_id = None
        atom = None

        # Preferred: (container_id, atom_dict)
        if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], dict):
            container_id = args[0]
            atom = dict(args[1])  # copy

        # Legacy A: (atom_dict)
        elif len(args) >= 1 and isinstance(args[0], dict):
            atom = dict(args[0])
            container_id = (
                atom.get("container")
                or atom.get("container_id")
                or getattr(self, "active_container_name", None)
            )

        # Legacy B: (atom_id, payload_dict)
        elif len(args) >= 2 and isinstance(args[0], (str, int)) and isinstance(args[1], dict):
            atom_id_str = str(args[0])
            payload = dict(args[1])
            payload.setdefault("id", atom_id_str)
            atom = payload
            container_id = (
                payload.get("container")
                or payload.get("container_id")
                or getattr(self, "active_container_name", None)
            )

        else:
            raise ValueError(
                "register_atom requires (container_id, atom_dict) or (atom_dict) or (id, payload)"
            )

        if not atom:
            raise ValueError("register_atom: missing atom payload")

        atom_id = atom.get("id")
        if not atom_id or not isinstance(atom_id, str):
            raise ValueError("register_atom: atom missing 'id' (str)")

        # Normalize fields commonly used by the route planner
        atom.setdefault("type", "atom")
        atom.setdefault("labels", [])
        atom.setdefault("meta", {})
        atom.setdefault("caps", list(atom.get("caps", [])) or list(atom["meta"].get("caps", [])) or [])
        atom.setdefault("nodes", list(atom.get("nodes", [])) or list(atom["meta"].get("nodes", [])) or [])
        # (tags are optional for scoring; include if present in meta)
        if "tags" not in atom and isinstance(atom["meta"].get("tags"), list):
            atom["tags"] = list(atom["meta"]["tags"])

        # Keep provenance
        if container_id:
            atom["container"] = container_id
            # Store under container too (safe even if container skeleton)
            try:
                if container_id not in self.containers:
                    self.register_container(container_id, {})
                self.containers[container_id].setdefault("atoms", {})
                self.containers[container_id]["atoms"][atom_id] = atom
            except Exception:
                pass

        # Always index by the ATOM id (not container id)
        if not hasattr(self, "atom_index") or self.atom_index is None:
            self.atom_index = {}
        self.atom_index[str(atom_id)] = atom

        # Address indexing + optional global registry (best-effort)
        try:
            meta = atom.get("meta") or {}
            address = meta.get("address") or atom.get("address")
            if isinstance(address, str) and address.strip():
                # local address index
                if not hasattr(self, "address_index") or self.address_index is None:
                    self.address_index = {}
                self.address_index[address] = atom_id
                # global registry (if available)
                try:
                    from backend.modules.dna_chain.container_index_writer import register_container_address
                    register_container_address(
                        atom_id,
                        address,
                        meta=meta,
                        kind=atom.get("type", "atom"),
                    )
                except Exception:
                    pass
        except Exception:
            pass

        return atom_id


    def _register_atom_compat(self, container_name: str, atom: dict):
        """
        Calls the appropriate register_atom implementation depending on its signature:
        • new: register_atom(self, container_name, atom)
        • old: register_atom(self, atom_id_or_obj, payload=None)
        Always preserves provenance and ensures atom is keyed by its own id.
        """
        import inspect

        # Ensure provenance on the payload
        a = dict(atom)
        a.setdefault("container", container_name)

        try:
            sig = inspect.signature(self.register_atom)
            params = list(sig.parameters)
            # self + container_name + atom  => length ≥ 3 → new form
            if len(params) >= 3:
                return self.register_atom(container_name, a)
            # else assume legacy (self, atom_dict, payload=None)
            return self.register_atom(a)
        except TypeError:
            # Fallback: try new then legacy
            try:
                return self.register_atom(container_name, a)
            except TypeError:
                return self.register_atom(a)


    def load_container_from_path(self, path: str, register_as_atom: bool = False) -> Dict[str, Any]:
        """
        Load a .dc.json (container or atom), normalize, stamp address + GHX/geometry,
        and ALWAYS index atoms by their own id (provenance kept).
        `register_as_atom` controls only any extra/persistent side-effects (NOT routing).
        """
        import os, json
        from json import JSONDecodeError

        # 1) Normalize & sanity-check path
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            raise ValueError(f"Container file not found: {path}")

        # 2) Robust JSON load
        with open(path, "r", encoding="utf-8") as f:
            try:
                obj = json.load(f)
            except JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {path}: {e}") from e

        if not isinstance(obj, dict):
            raise ValueError(f"Root must be an object, got {type(obj).__name__}")

        # 3) Compute container id early (stable)
        cid = (
            obj.get("container_id")
            or obj.get("id")
            or os.path.basename(path).replace(".dc.json", "")
        )
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError(f"Could not determine container id for {path}")
        obj["id"] = cid

        # 4) Normalize atoms → list[dict] with ids; deterministic order
        atoms = obj.get("atoms")
        if isinstance(atoms, dict):
            atoms = [atoms]
        atoms = atoms or []
        atoms_clean = [a for a in atoms if isinstance(a, dict)]
        atoms_sorted = sorted(atoms_clean, key=lambda a: str(a.get("id", "")))
        obj["atoms"] = atoms_sorted
        obj["atom_ids"] = [str(a.get("id")) for a in atoms_sorted if a.get("id")]

        # 5) Register container (keeps your address/wormhole behavior)
        self.register_container(cid, obj)

        # 6) Best-effort hooks (don’t fail the load)
        try:
            self._ghx_register_once(cid, name=cid)
        except Exception:
            pass
        try:
            self.geometry_loader.register_geometry(
                cid,
                obj.get("symbol", "❔"),
                obj.get("geometry", "default"),
            )
        except Exception:
            pass

        # 7) ALWAYS index atoms for routing (by atom id) + keep provenance
        for a in atoms_sorted:
            try:
                a.setdefault("container", cid)
                # FIX: pass container id to the compat shim
                self._register_atom_compat(cid, a)
            except Exception as e:
                print(f"[UCS] Skipped atom {a.get('id','<no-id>')} in {cid}: {e}")

        # 8) Optional extra persistence/registry (NOT needed for routing)
        if register_as_atom:
            try:
                # place any persistence/global-registry writes here if you use them
                # (Do NOT register the container itself as an atom.)
                pass
            except Exception:
                pass

        # 9) Make this the active container for convenience
        self.active_container_name = cid
        return obj

# ---- Minimal path planner (only add if you don't already have one) ---------
    def compose_path(self, goal: dict, k: int = 3) -> list[str]:
        want_caps  = set(goal.get("caps", []))
        want_nodes = set(goal.get("nodes", []))
        want_tags  = set(goal.get("tags", []))

        if not getattr(self, "atom_index", None):
            return []

        scored = []
        for atom_id, meta in self.atom_index.items():
            # meta could be a tuple in very old states; normalize to dict
            if isinstance(meta, tuple) and len(meta) == 2 and isinstance(meta[1], dict):
                meta = meta[1]
            caps  = set(meta.get("caps", []))
            nodes = set(meta.get("nodes", []))
            tags  = set(meta.get("tags", []))
            score = 2.0 * len(want_caps & caps) + 1.0 * len(want_nodes & nodes) + 0.5 * len(want_tags & tags)
            if score > 0:
                scored.append((score, atom_id))

        scored.sort(key=lambda t: (-t[0], t[1]))
        return [aid for _, aid in scored[:k]]

    # ─────────────────────────────────────────────────────────────────────────
    # Registration helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _as_list(self, v):
        if v is None:
            return []
        if isinstance(v, (list, tuple, set)):
            return [str(x) for x in v]
        return [str(v)]

    def _iter_atom_meta(self):
        """
        Yield (atom_id, meta_dict) for scoring, normalizing both tuple-style and dict-style entries.
        - Tuple: (container_name, atom_obj)
        - Dict:  {"container": "...", "ref"/"atom": {...}}  or raw atom dict
        """
        atom_index = getattr(self, "atom_index", {}) or {}
        for atom_id, entry in atom_index.items():
            container_name = None
            atom_obj = None

            if isinstance(entry, tuple) and len(entry) == 2:
                container_name, atom_obj = entry
            elif isinstance(entry, dict):
                container_name = entry.get("container") or entry.get("container_id")
                atom_obj = entry.get("ref") or entry.get("atom") or entry
            else:
                atom_obj = entry  # last resort

            if not isinstance(atom_obj, dict):
                continue

            # Merge meta if present, but keep top-level fields available
            meta = dict(atom_obj)
            if isinstance(atom_obj.get("meta"), dict):
                meta = {**atom_obj["meta"], **{k: v for k, v in atom_obj.items() if k != "meta"}}

            # Normalize lists
            meta.setdefault("caps",  self._as_list(meta.get("caps")))
            meta.setdefault("nodes", self._as_list(meta.get("nodes")))
            meta.setdefault("tags",  self._as_list(meta.get("tags")))

            # Preserve provenance
            if container_name:
                meta.setdefault("container", container_name)

            # Ensure id survives for any downstream debug
            meta.setdefault("id", atom_id)

            yield atom_id, meta

    def load_dc_container(self, path: str, register_as_atom: bool = False) -> Dict[str, Any]:
        """Back-compat alias for older callers."""
        return self.load_container_from_path(path, register_as_atom=register_as_atom)

    def load_container(self, path_or_name: str, register_as_atom: bool = False) -> Dict[str, Any]:
        """
        Back-compat loader:
        - If `path_or_name` is a file → delegate to load_container_from_path()
        - Else treat it as a container name → return the registered container (or {})
        Always keeps routing indexes up to date via the underlying loader.
        """
        # File path → modern loader
        try:
            if isinstance(path_or_name, str) and os.path.isfile(path_or_name):
                return self.load_container_from_path(path_or_name, register_as_atom=register_as_atom)
        except Exception:
            # Fall through to name mode if os.path checks explode for any reason
            pass

        # Name mode → return whatever we have (don’t raise, for legacy callers)
        name = str(path_or_name)
        return self.containers.get(name, {})

    # ─────────────────────────────────────────────────────────────────────────
    # Debug snapshot (used by /ucs/debug)
    # ─────────────────────────────────────────────────────────────────────────
    def debug_snapshot(self) -> Dict[str, Any]:
        return {
            "containers": list(self.containers.keys()),
            "active_container": self.active_container_name,
            "atom_index_count": len(self.atom_index),
            "atom_ids": list(self.atom_index.keys()),
            "addresses": registry_list_addresses() or list(self.address_index.keys()),
            "atom_dir_exists": os.path.isdir(os.path.join("backend", "data", "ucs", "atoms")),
            "atom_dir_path": os.path.join(os.getcwd(), "backend", "data", "ucs", "atoms"),
        }

    def choose_route(self, goal: Dict[str, Any], k: int = 3, explain: bool = False) -> Dict[str, Any]:
        """
        Simple wrapper (default) that returns a minimal plan,
        with an optional 'explain=True' to attach rationale.
        """
        atom_ids = self.compose_path(goal, k=k)

        result: Dict[str, Any] = {
            "goal": goal,
            "atoms": atom_ids,
            "plan": [{"atom_id": a, "mode": "sequential"} for a in atom_ids],
        }

        if explain:
            result["rationale"] = self._build_route_rationale(goal, atom_ids)

        return result

    def _build_route_rationale(self, goal: Dict[str, Any], atom_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Preserves your previous verbose rationale logic (no code loss).
        Builds the human-readable overlap/score details for the chosen atom_ids.
        """
        want_caps  = set(goal.get("caps", []))
        want_nodes = set(goal.get("nodes", []))
        want_tags  = set(goal.get("tags", []))

        rationale: List[Dict[str, Any]] = []
        for atom_id in atom_ids:
            meta = self.atom_index.get(atom_id, {})

            # Back-compat: some installs stored (id, meta) tuples in atom_index
            if isinstance(meta, tuple) and len(meta) == 2 and isinstance(meta[1], dict):
                meta = meta[1]

            caps  = set(meta.get("caps", []))
            nodes = set(meta.get("nodes", []))
            tags  = set(meta.get("tags", []))

            cap_overlap  = sorted(list(want_caps  & caps))
            node_overlap = sorted(list(want_nodes & nodes))
            tag_overlap  = sorted(list(want_tags  & tags))

            # Keep the same weight formula used by compose_path()
            score = 2.0 * len(cap_overlap) + 1.0 * len(node_overlap) + 0.5 * len(tag_overlap)

            entry = {
                "atom_id": atom_id,
                "container": meta.get("container"),
                "score": score,
                "overlap": {
                    "caps": cap_overlap,
                    "nodes": node_overlap,
                    "tags": tag_overlap,
                },
                "labels": meta.get("labels", []),
                "title": meta.get("title") or meta.get("name"),
            }
            rationale.append(entry)

            # Server-side breadcrumb (safe + concise)
            try:
                print(
                    f"[RoutePlanner] atom={atom_id} score={score:.2f} "
                    f"caps={cap_overlap} nodes={node_overlap} tags={tag_overlap} "
                    f"container={entry['container']}"
                )
            except Exception:
                pass

        return rationale

    def _route_with_fallback(runtime, goal: dict, k: int = 3):
        # Prefer built-ins if they exist
        if hasattr(runtime, "choose_route"):
            return runtime.choose_route(goal, k=k)
        if hasattr(runtime, "compose_path"):
            atom_ids = runtime.compose_path(goal, k=k)
            return {
                "goal": goal,
                "atoms": atom_ids,
                "plan": [{"atom_id": a, "mode": "sequential"} for a in atom_ids],
            }

        # Fallback scorer (same weights you’ve been using)
        want_caps  = set(goal.get("caps", []))
        want_nodes = set(goal.get("nodes", []))
        want_tags  = set(goal.get("tags", []))

        scored = []
        for aid, m in (runtime.atom_index or {}).items():
            # Normalize legacy tuple shape: (container_name, meta_dict)
            if isinstance(m, tuple) and len(m) == 2 and isinstance(m[1], dict):
                m = m[1]
            caps  = set(m.get("caps", []))
            nodes = set(m.get("nodes", []))
            tags  = set(m.get("tags", []))
            score = 2.0 * len(want_caps & caps) + 1.0 * len(want_nodes & nodes) + 0.5 * len(want_tags & tags)
            if score > 0:
                scored.append((score, aid))

        scored.sort(key=lambda t: (-t[0], t[1]))
        atom_ids = [aid for _, aid in scored[:k]]
        return {
            "goal": goal,
            "atoms": atom_ids,
            "plan": [{"atom_id": a, "mode": "sequential"} for a in atom_ids],
        }

    def save_container(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save container state into runtime memory (idempotent)."""
        # keep original behavior
        self.containers[name] = data
        self.active_container_name = name  # mark active on save

        # ⬇️ enforce address + hub wormhole + global registry
        try:
            self._ensure_address_and_wormhole(name, self.containers[name])
        except Exception:
            pass

        # ⬇️ maintain optional container_index (if present in this runtime)
        try:
            idx = getattr(self, "container_index", None)
            if isinstance(idx, dict):
                meta = self.containers[name].get("meta") or {}
                idx[name] = {
                    "id": name,
                    "address": meta.get("address"),
                    "type": self.containers[name].get("type", "container"),
                }
        except Exception:
            pass

        # ⬇️ optional: notify visualizer (safe no-op if stubbed)
        try:
            if getattr(self, "visualizer", None):
                self.visualizer.log_event(name, "container_saved")
        except Exception:
            pass

        return self.containers[name]

    def remove_container(self, container_id: str) -> Dict[str, Any]:
        """
        Remove a container from the UCS runtime.

        Cleans:
        • self.containers[container_id]
        • self.atom_index entries belonging to that container
        • self.address_index mappings for that container’s address(es)
        • reverse wormhole references from other containers
        • self.container_index (if present)
        • active_container_name fallback to hub (if needed)

        Also attempts to unregister from the global address registry.
        Returns a summary dict.
        """
        if container_id not in self.containers:
            return {"ok": False, "reason": "not_found", "container_id": container_id}

        if container_id == DEFAULT_HUB_ID:
            return {"ok": False, "reason": "cannot_remove_hub", "container_id": container_id}

        container = self.containers[container_id]

        # -- purge atom_index entries for this container
        removed_atom_ids = []
        try:
            for aid, entry in list(self.atom_index.items()):
                if isinstance(entry, tuple) and len(entry) == 2:
                    if entry[0] == container_id:
                        removed_atom_ids.append(aid)
                        del self.atom_index[aid]
                elif isinstance(entry, dict):
                    if entry.get("container") == container_id or entry.get("container_id") == container_id:
                        removed_atom_ids.append(aid)
                        del self.atom_index[aid]
        except Exception:
            # keep removal resilient
            pass

        # -- remove address mappings
        removed_addresses: List[str] = []
        try:
            meta = container.get("meta") or {}
            addr = meta.get("address")
            if isinstance(addr, str) and self.address_index.get(addr) == container_id:
                del self.address_index[addr]
                removed_addresses.append(addr)

            # in case there are stray mappings pointing to this container
            for a, cid in list(self.address_index.items()):
                if cid == container_id and a not in removed_addresses:
                    del self.address_index[a]
                    removed_addresses.append(a)
        except Exception:
            pass

        # -- remove reverse wormhole refs from other containers
        try:
            for other_id, other in self.containers.items():
                if other_id == container_id:
                    continue
                wl = other.get("wormholes")
                if isinstance(wl, list) and container_id in wl:
                    other["wormholes"] = [w for w in wl if w != container_id]
        except Exception:
            pass

        # -- remove from optional container_index
        try:
            idx = getattr(self, "container_index", None)
            if isinstance(idx, dict) and container_id in idx:
                del idx[container_id]
        except Exception:
            pass

        # -- finally, delete the container
        del self.containers[container_id]

        # -- move active pointer if needed
        if getattr(self, "active_container_name", None) == container_id:
            self.active_container_name = DEFAULT_HUB_ID if DEFAULT_HUB_ID in self.containers else None

        # -- unregister from global registry
        try:
            registry_unregister_container(container_id)
        except Exception:
            pass

        # -- visualizer notice (safe no-op if stubbed)
        try:
            if getattr(self, "visualizer", None):
                self.visualizer.log_event(container_id, "container_removed")
        except Exception:
            pass

        return {
            "ok": True,
            "removed": container_id,
            "removed_atoms": len(removed_atom_ids),
            "removed_addresses": removed_addresses,
            "active_container": self.active_container_name,
        }

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
    # 🧩 Atom registration + path composition (FINAL)
    # ---------------------------------------------------------
    def register_container(
        self,
        container_name: str,
        container_data: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Ensure a container record exists, is safely (re)merged, and ready to host atoms.
        - Idempotent (safe to call many times)
        - Keeps existing fields unless explicitly overwritten by container_data
        - Always provides `atoms` dict
        - Enforces meta.address + hub wormhole + registry entry
        - Maintains optional container_index (if present)
        Returns the (updated) container dict.
        """
        # Pull existing instance if present
        existing = self.containers.get(container_name, {}) or {}

        # Normalize incoming data
        if container_data is None:
            container_data = {}
        container_data.setdefault("id", container_name)
        container_data.setdefault("type", existing.get("type", "container"))

        # Merge shallow (prefer new keys, retain prior unless overwritten)
        merged = {**existing, **container_data}

        # Always ensure atoms bucket
        merged.setdefault("atoms", {})

        # Save to runtime container registry
        self.containers[container_name] = merged

        # Ensure address + wormhole + global registry link
        try:
            self._ensure_address_and_wormhole(container_name, merged)
        except Exception:
            # Non-fatal — runtime must remain resilient
            pass

        # Update container_index (if runtime maintains one)
        try:
            idx = getattr(self, "container_index", None)
            if isinstance(idx, dict):
                meta = merged.get("meta") or {}
                idx[container_name] = {
                    "id": container_name,
                    "address": meta.get("address"),
                    "type": merged.get("type", "container"),
                }
        except Exception:
            pass

        # Notify visualizer (safe no-op if unavailable)
        try:
            if getattr(self, "visualizer", None):
                self._ghx_register_once(merged.get("id") or merged.get("name") or cid, merged.get("name"))
        except Exception:
            pass

        return merged

    
    def resolve_atom(self, key: str) -> Optional[str]:
        """
        Accepts atom_id or ucs://address and returns atom_id if known.
        Checks local atom_index, local address_index, then global registry.
        """
        if not key:
            return None

        # 1) Direct atom id
        if key in self.atom_index:
            return key

        # 2) Local address index (address → container_id/atom_id)
        hit = self.address_index.get(key)
        if hit:
            # Might be a container id; if this is also an atom id, return it, else pass-through
            if hit in self.atom_index:
                return hit
            # Fallback: allow routing to container id as atom id if naming convention matches
            return hit

        # 3) Global registry lookup (address → container_id)
        try:
            resolved = resolve_by_address(key)
            return resolved
        except Exception:
            return None

    def debug_state(self) -> Dict[str, Any]:
        # Prefer container_index if present; otherwise fall back to in-memory containers
        try:
            containers_list = list(getattr(self, "container_index", {}).keys())
            if not containers_list:
                containers_list = list(getattr(self, "containers", {}).keys())
        except Exception:
            containers_list = list(getattr(self, "containers", {}).keys())

        # Active container (support both legacy and new field names)
        active = getattr(self, "active_container_name", None) or getattr(self, "active_container", None)

        # Local addresses from in-memory index
        local_addrs = list(getattr(self, "address_index", {}).keys())

        # Registry addresses (global)
        try:
            # registry_list_addresses() expected to yield iterable of (container_id, address)
            registry_addrs = [addr for (_cid, addr) in registry_list_addresses()]
        except Exception:
            registry_addrs = []

        # Atom index details
        atom_idx = getattr(self, "atom_index", {}) or {}

        return {
            "containers": containers_list,
            "active_container": active,
            "atom_index_count": len(atom_idx),
            "atom_ids": list(atom_idx.keys()),
            "addresses": sorted(set(local_addrs + registry_addrs)),
        }

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
        Greedy scorer: 2*cap + 1*node + 0.5*tag overlap.
        Returns top-k atom IDs.
        """
        if not getattr(self, "atom_index", None):
            return []

        want_caps  = set(goal.get("caps", []))
        want_nodes = set(goal.get("nodes", []))
        want_tags  = set(goal.get("tags", []))

        scored: List[Tuple[float, str]] = []
        for atom_id, meta in self.atom_index.items():
            # Legacy tuple form support: (container_name, atom_dict)
            if isinstance(meta, tuple) and len(meta) == 2 and isinstance(meta[1], dict):
                meta = meta[1]

            caps  = set(meta.get("caps", []))
            nodes = set(meta.get("nodes", []))
            tags  = set(meta.get("tags", []))

            score = 2.0 * len(want_caps & caps) + 1.0 * len(want_nodes & nodes) + 0.5 * len(want_tags & tags)
            if score > 0.0:
                scored.append((score, atom_id))

        scored.sort(key=lambda t: (-t[0], t[1]))
        return [aid for _, aid in scored[:k]]

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

    def embed_glyph_block_into_container(self, name: str, glyph_block: Any):
        """Embed glyph block (legacy alias for Codex injection)."""
        c = self.get_container(name)
        c.setdefault("glyphs", []).append(glyph_block)
        self.save_container(name, c)

# ---------------------------------------------------------
# ✅ Singleton + Safe Legacy Aliases
# ---------------------------------------------------------
ucs_runtime = UCSRuntime()

# Optional SQIRuntime alias — only create if truly needed
try:
    SQIRuntime = UCSRuntime
    ucs_runtime.sqi = SQIRuntime()
except Exception as e:
    # SQIRuntime not essential; log or ignore
    pass

# ─────────────────────────────
# Singleton + public API start
# ─────────────────────────────
from typing import Optional  # ignore if already imported at top

_ucs_singleton: Optional["UCSRuntime"] = None

def get_ucs_runtime() -> "UCSRuntime":
    global _ucs_singleton
    if _ucs_singleton is None:
        _ucs_singleton = UCSRuntime()
    return _ucs_singleton

# Back-compat name: some code imports this directly
ucs_runtime = get_ucs_runtime()

# ---------------------------------------------------------
# Legacy compatibility shims (safe getattr so missing attrs don't break import)
# ---------------------------------------------------------
def _alias(name: str):
    """Return bound UCSRuntime method if it exists, else raise AttributeError on call."""
    attr = getattr(ucs_runtime, name, None)
    if callable(attr):
        return attr

    def _missing(*args, **kwargs):
        raise NotImplementedError(f"{name} is not implemented in UCSRuntime")
    return _missing



# Optional legacy aliases
load_dc_container = _alias("load_container_from_path")
load_container_from_path = _alias("load_container_from_path")  # optional duplicate
load_container = _alias("load_container")                      
expand_container = _alias("expand_container")
collapse_container = _alias("collapse_container")
embed_glyph_block_into_container = _alias("embed_glyph_block_into_container")

# ---------------------------------------------------------
# ✅ Public API
# ---------------------------------------------------------
__all__ = [
    "UCSRuntime",
    "ucs_runtime",
    "get_ucs_runtime",
    "load_dc_container",
    "load_container_from_path",
    "expand_container",
    "collapse_container",
    "embed_glyph_block_into_container",
]