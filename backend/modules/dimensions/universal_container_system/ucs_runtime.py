"""
🧮 UCS Runtime
-----------------------------------------------------
Handles:
    * Container loading/execution
    * GHXVisualizer integration
    * SQI runtime + Pi GPIO event output
    * SoulLaw enforcement
    * Geometry registration + trigger map events
    * Legacy container_runtime API compatibility
"""

from __future__ import annotations

import os
import json
import inspect
import uuid
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from json import JSONDecodeError

logger = logging.getLogger("UCSRuntime")

# Core subsystems
from backend.modules.dimensions.universal_container_system.ucs_utils import normalize_container_dict
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCSGeometryLoader
from backend.modules.dimensions.universal_container_system.ucs_soullaw import SoulLawEnforcer
from backend.modules.dimensions.universal_container_system.ucs_trigger_map import UCSTriggerMap

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


class _SQIStub:
    """Safe default so callers doing `runtime.sqi.emit(...)` don't crash when SQI isn't wired."""
    def emit(self, *_a, **_k):
        return None


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
def get_sqi_registry():
    """
    Safe, deferred import of SQIContainerRegistry to avoid circular imports
    between UCSRuntime and SQI modules.
    """
    try:
        from backend.modules.sqi.sqi_container_registry import SQIContainerRegistry
        return SQIContainerRegistry()
    except Exception as e:
        logging.getLogger("UCSRuntime").warning(f"[UCS] SQI registry unavailable: {e}")
        return None


class UCSRuntime:
    def __init__(self) -> None:
        self.containers: Dict[str, Dict[str, Any]] = {}
        self.atom_index: Dict[str, Any] = {}
        self.address_index: Dict[str, str] = {}

        # Optional runtime hooks
        self.sqi = _SQIStub()
        self.visualizer = GHXVisualizer()
        self.geometry_loader = UCSGeometryLoader()
        self.soul_law = SoulLawEnforcer()
        self.trigger_map = UCSTriggerMap()
        self._ghx_registered: set[str] = set()

        self.active_container_name: Optional[str] = None

        # ✅ FIXED: lazy load to prevent circular import
        self.container_registry = get_sqi_registry()

        # Ensure a minimal hub exists and is registered once
        if DEFAULT_HUB_ID not in self.containers:
            self.register_container(DEFAULT_HUB_ID, {"meta": {"domain": "ucs/default"}})
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

    # ─────────────────────────────────────────────────────────────────────────
    # Telemetry taps (best-effort, never break runtime)
    # ─────────────────────────────────────────────────────────────────────────
    def _kg_emit(self, glyph_type: str, content: Any, *, tags: Optional[List[str]] = None) -> None:
        try:
            from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
            kg = get_kg_writer()
        except Exception:
            return
        try:
            if hasattr(kg, "inject_glyph"):
                kg.inject_glyph(
                    content=content,
                    glyph_type=glyph_type,
                    metadata={"container_id": self.active_container_name or "ucs_runtime"},
                    tags=tags or ["ucs"],
                    agent_id="ucs_runtime",
                )
            elif hasattr(kg, "write_glyph_entry"):
                kg.write_glyph_entry({
                    "id": f"ucs_{uuid.uuid4().hex}",
                    "type": glyph_type,
                    "content": content,
                    "timestamp": time.time(),
                    "metadata": {"tags": tags or ["ucs"]},
                })
        except Exception:
            pass

    def _mg_register(
        self,
        glyph: str,
        *,
        meta: Optional[Dict[str, Any]] = None,
        x: int = 0,
        y: int = 0,
        z: int = 0,
        t: Optional[int] = None,
    ) -> None:
        try:
            from backend.modules.glyphos.microgrid_index import MicrogridIndex
            MG = getattr(MicrogridIndex, "_GLOBAL", None) or MicrogridIndex()
            MicrogridIndex._GLOBAL = MG
        except Exception:
            return
        try:
            MG.register_glyph(
                int(x) % 16,
                int(y) % 16,
                int(z) % 16,
                glyph=str(glyph),
                layer=int(t) if t is not None else None,
                metadata={
                    "type": (meta or {}).get("type", "ucs"),
                    "tags": (meta or {}).get("tags", ["ucs"]),
                    **(meta or {}),
                },
            )
        except Exception:
            pass

    def register(self, container):
        """Register a container into the UCS runtime system."""
        cid = getattr(container, "id", None)
        if not cid:
            raise ValueError("Cannot register container without an ID.")

        if hasattr(container, "to_dict") and callable(getattr(container, "to_dict")):
            self.containers[cid] = container.to_dict()
        elif isinstance(container, dict):
            self.containers[cid] = container
        else:
            self.containers[cid] = {"id": cid, "name": getattr(container, "name", cid), "type": "container"}

        print(f"📦 [UCS] Registered container '{cid}'")

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

        meta = data.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            data["meta"] = meta

        ctype = data.get("type", "container")

        addr = meta.get("address")
        if not isinstance(addr, str) or not addr.strip():
            addr = f"ucs://local/{container_id}#{ctype}"
            meta["address"] = addr

        wormholes = data.get("wormholes")
        if not isinstance(wormholes, list):
            wormholes = []
            data["wormholes"] = wormholes

        if DEFAULT_HUB_ID not in wormholes and container_id != DEFAULT_HUB_ID:
            wormholes.append(DEFAULT_HUB_ID)
            try:
                link_wormhole(container_id, DEFAULT_HUB_ID, meta={"reason": "auto_hub"})
            except Exception as e:
                print(f"[UCS] link_wormhole({container_id}->{DEFAULT_HUB_ID}) failed: {e!r}")

        self.address_index[addr] = container_id

        try:
            register_container_address(container_id, addr, meta=meta, kind=ctype)
        except Exception as e:
            print(f"[UCS] register_container_address({container_id}, {addr}) failed: {e!r}")

    # ─────────────────────────────────────────────────────────────────────────
    # Atom registration
    # ─────────────────────────────────────────────────────────────────────────
    def register_atom(self, *args, **kwargs) -> str:
        """
        Canonical + back-compat shim.

        Preferred:  register_atom(container_id: str, atom: dict) -> id
        Legacy A:   register_atom(atom_dict) -> id
        Legacy B:   register_atom(atom_id, payload_dict) -> id
        """
        container_id = None
        atom = None

        if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], dict):
            container_id = args[0]
            atom = dict(args[1])
        elif len(args) >= 1 and isinstance(args[0], dict):
            atom = dict(args[0])
            container_id = atom.get("container") or atom.get("container_id") or getattr(self, "active_container_name", None)
        elif len(args) >= 2 and isinstance(args[0], (str, int)) and isinstance(args[1], dict):
            atom_id_str = str(args[0])
            payload = dict(args[1])
            payload.setdefault("id", atom_id_str)
            atom = payload
            container_id = payload.get("container") or payload.get("container_id") or getattr(self, "active_container_name", None)
        else:
            raise ValueError("register_atom requires (container_id, atom_dict) or (atom_dict) or (id, payload)")

        if not atom:
            raise ValueError("register_atom: missing atom payload")

        atom_id = atom.get("id")
        if not atom_id or not isinstance(atom_id, str):
            raise ValueError("register_atom: atom missing 'id' (str)")

        atom.setdefault("type", "atom")
        atom.setdefault("labels", [])
        atom.setdefault("meta", {})
        atom.setdefault("caps", list(atom.get("caps", [])) or list(atom["meta"].get("caps", [])) or [])
        atom.setdefault("nodes", list(atom.get("nodes", [])) or list(atom["meta"].get("nodes", [])) or [])
        if "tags" not in atom and isinstance(atom["meta"].get("tags"), list):
            atom["tags"] = list(atom["meta"]["tags"])

        if container_id:
            atom["container"] = container_id
            try:
                if container_id not in self.containers:
                    self.register_container(container_id, {})
                self.containers[container_id].setdefault("atoms", {})
                self.containers[container_id]["atoms"][atom_id] = atom
            except Exception:
                pass

        if not hasattr(self, "atom_index") or self.atom_index is None:
            self.atom_index = {}
        self.atom_index[str(atom_id)] = atom

        try:
            meta = atom.get("meta") or {}
            address = meta.get("address") or atom.get("address")
            if isinstance(address, str) and address.strip():
                if not hasattr(self, "address_index") or self.address_index is None:
                    self.address_index = {}
                self.address_index[address] = atom_id
                try:
                    register_container_address(atom_id, address, meta=meta, kind=atom.get("type", "atom"))
                except Exception:
                    pass
        except Exception:
            pass

        return atom_id

    def _register_atom_compat(self, container_name: str, atom: dict):
        a = dict(atom)
        a.setdefault("container", container_name)
        try:
            sig = inspect.signature(self.register_atom)
            params = list(sig.parameters)
            if len(params) >= 3:
                return self.register_atom(container_name, a)
            return self.register_atom(a)
        except TypeError:
            try:
                return self.register_atom(container_name, a)
            except TypeError:
                return self.register_atom(a)

    # ─────────────────────────────────────────────────────────────────────────
    # Container loading
    # ─────────────────────────────────────────────────────────────────────────
    def load_container_from_path(self, path: str, register_as_atom: bool = False) -> Dict[str, Any]:
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            raise ValueError(f"Container file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            try:
                obj = json.load(f)
            except JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {path}: {e}") from e

        if not isinstance(obj, dict):
            raise ValueError(f"Root must be an object, got {type(obj).__name__}")

        cid = obj.get("container_id") or obj.get("id") or os.path.basename(path).replace(".dc.json", "")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError(f"Could not determine container id for {path}")
        obj["id"] = cid

        atoms = obj.get("atoms")
        if isinstance(atoms, dict):
            atoms = [atoms]
        atoms = atoms or []
        atoms_clean = [a for a in atoms if isinstance(a, dict)]
        atoms_sorted = sorted(atoms_clean, key=lambda a: str(a.get("id", "")))
        obj["atoms"] = atoms_sorted
        obj["atom_ids"] = [str(a.get("id")) for a in atoms_sorted if a.get("id")]

        self.register_container(cid, obj)

        try:
            self._ghx_register_once(cid, name=cid)
        except Exception:
            pass
        try:
            self.geometry_loader.register_geometry(cid, obj.get("symbol", "❔"), obj.get("geometry", "default"))
        except Exception:
            pass

        for a in atoms_sorted:
            try:
                a.setdefault("container", cid)
                self._register_atom_compat(cid, a)
            except Exception as e:
                print(f"[UCS] Skipped atom {a.get('id','<no-id>')} in {cid}: {e}")

        if register_as_atom:
            try:
                pass
            except Exception:
                pass

        try:
            self._kg_emit("ucs_load_container", {"id": cid, "atom_count": len(obj.get("atom_ids", []))}, tags=["ucs", "load"])
        except Exception:
            pass

        self.active_container_name = cid
        return obj

    # ─────────────────────────────────────────────────────────────────────────
    # Routing
    # ─────────────────────────────────────────────────────────────────────────
    def compose_path(self, goal: dict, k: int = 3) -> list[str]:
        want_caps = set(goal.get("caps", []))
        want_nodes = set(goal.get("nodes", []))
        want_tags = set(goal.get("tags", []))

        if not getattr(self, "atom_index", None):
            return []

        scored: List[Tuple[float, str]] = []
        for atom_id, meta in self.atom_index.items():
            if isinstance(meta, tuple) and len(meta) == 2 and isinstance(meta[1], dict):
                meta = meta[1]
            if not isinstance(meta, dict):
                continue
            caps = set(meta.get("caps", []))
            nodes = set(meta.get("nodes", []))
            tags = set(meta.get("tags", []))
            score = 2.0 * len(want_caps & caps) + 1.0 * len(want_nodes & nodes) + 0.5 * len(want_tags & tags)
            if score > 0:
                scored.append((score, atom_id))

        scored.sort(key=lambda t: (-t[0], t[1]))
        return [aid for _, aid in scored[:k]]

    def _as_list(self, v):
        if v is None:
            return []
        if isinstance(v, (list, tuple, set)):
            return [str(x) for x in v]
        return [str(v)]

    def _iter_atom_meta(self):
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
                atom_obj = entry

            if not isinstance(atom_obj, dict):
                continue

            meta = dict(atom_obj)
            if isinstance(atom_obj.get("meta"), dict):
                meta = {**atom_obj["meta"], **{k: v for k, v in atom_obj.items() if k != "meta"}}

            meta.setdefault("caps", self._as_list(meta.get("caps")))
            meta.setdefault("nodes", self._as_list(meta.get("nodes")))
            meta.setdefault("tags", self._as_list(meta.get("tags")))

            if container_name:
                meta.setdefault("container", container_name)
            meta.setdefault("id", atom_id)

            yield atom_id, meta

    # ─────────────────────────────────────────────────────────────────────────
    # Legacy loaders
    # ─────────────────────────────────────────────────────────────────────────
    def load_dc_container(self, path: str, register_as_atom: bool = False) -> Dict[str, Any]:
        return self.load_container_from_path(path, register_as_atom=register_as_atom)

    def load_container(self, path_or_name: str, register_as_atom: bool = False) -> Dict[str, Any]:
        try:
            if isinstance(path_or_name, str) and os.path.isfile(path_or_name):
                return self.load_container_from_path(path_or_name, register_as_atom=register_as_atom)
        except Exception:
            pass
        name = str(path_or_name)
        return self.containers.get(name, {})

    # ─────────────────────────────────────────────────────────────────────────
    # Debug
    # ─────────────────────────────────────────────────────────────────────────
    def debug_snapshot(self) -> Dict[str, Any]:
        return {
            "containers": list(self.containers.keys()),
            "active_container": self.active_container_name,
            "atom_index_count": len(self.atom_index),
            "atom_ids": list(self.atom_index.keys()),
            "addresses": (registry_list_addresses() or list(self.address_index.keys())),
            "atom_dir_exists": os.path.isdir(os.path.join("backend", "data", "ucs", "atoms")),
            "atom_dir_path": os.path.join(os.getcwd(), "backend", "data", "ucs", "atoms"),
        }

    def choose_route(self, goal: Dict[str, Any], k: int = 3, explain: bool = False) -> Dict[str, Any]:
        atom_ids = self.compose_path(goal, k=k)

        result: Dict[str, Any] = {
            "goal": goal,
            "atoms": atom_ids,
            "plan": [{"atom_id": a, "mode": "sequential"} for a in atom_ids],
        }

        if explain:
            result["rationale"] = self._build_route_rationale(goal, atom_ids)

        try:
            if explain:
                self._kg_emit("ucs_route_plan", {"goal": goal, "atoms": atom_ids}, tags=["ucs", "route"])
        except Exception:
            pass

        return result

    def _build_route_rationale(self, goal: Dict[str, Any], atom_ids: List[str]) -> List[Dict[str, Any]]:
        want_caps = set(goal.get("caps", []))
        want_nodes = set(goal.get("nodes", []))
        want_tags = set(goal.get("tags", []))

        rationale: List[Dict[str, Any]] = []
        for atom_id in atom_ids:
            meta = self.atom_index.get(atom_id, {})
            if isinstance(meta, tuple) and len(meta) == 2 and isinstance(meta[1], dict):
                meta = meta[1]
            if not isinstance(meta, dict):
                meta = {}

            caps = set(meta.get("caps", []))
            nodes = set(meta.get("nodes", []))
            tags = set(meta.get("tags", []))

            cap_overlap = sorted(list(want_caps & caps))
            node_overlap = sorted(list(want_nodes & nodes))
            tag_overlap = sorted(list(want_tags & tags))

            score = 2.0 * len(cap_overlap) + 1.0 * len(node_overlap) + 0.5 * len(tag_overlap)

            entry = {
                "atom_id": atom_id,
                "container": meta.get("container") or meta.get("container_id"),
                "score": score,
                "overlap": {"caps": cap_overlap, "nodes": node_overlap, "tags": tag_overlap},
                "labels": meta.get("labels", []),
                "title": meta.get("title") or meta.get("name"),
            }
            rationale.append(entry)

            try:
                print(
                    f"[RoutePlanner] atom={atom_id} score={score:.2f} "
                    f"caps={cap_overlap} nodes={node_overlap} tags={tag_overlap} "
                    f"container={entry['container']}"
                )
            except Exception:
                pass

        return rationale

    @staticmethod
    def _route_with_fallback(runtime, goal: dict, k: int = 3):
        if hasattr(runtime, "choose_route"):
            return runtime.choose_route(goal, k=k)
        if hasattr(runtime, "compose_path"):
            atom_ids = runtime.compose_path(goal, k=k)
            return {"goal": goal, "atoms": atom_ids, "plan": [{"atom_id": a, "mode": "sequential"} for a in atom_ids]}

        want_caps = set(goal.get("caps", []))
        want_nodes = set(goal.get("nodes", []))
        want_tags = set(goal.get("tags", []))

        scored = []
        for aid, m in (getattr(runtime, "atom_index", {}) or {}).items():
            if isinstance(m, tuple) and len(m) == 2 and isinstance(m[1], dict):
                m = m[1]
            if not isinstance(m, dict):
                continue
            caps = set(m.get("caps", []))
            nodes = set(m.get("nodes", []))
            tags = set(m.get("tags", []))
            score = 2.0 * len(want_caps & caps) + 1.0 * len(want_nodes & nodes) + 0.5 * len(want_tags & tags)
            if score > 0:
                scored.append((score, aid))

        scored.sort(key=lambda t: (-t[0], t[1]))
        atom_ids = [aid for _, aid in scored[:k]]
        return {"goal": goal, "atoms": atom_ids, "plan": [{"atom_id": a, "mode": "sequential"} for a in atom_ids]}

    # ─────────────────────────────────────────────────────────────────────────
    # Persistence / state
    # ─────────────────────────────────────────────────────────────────────────
    def save_container(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save container state into runtime memory (idempotent)."""
        if not isinstance(data, dict):
            data = normalize_container_dict(data)
        data.setdefault("id", name)
        data.setdefault("meta", {})

        self.containers[name] = data
        self.active_container_name = name

        try:
            self._ensure_address_and_wormhole(name, self.containers[name])
        except Exception:
            pass

        try:
            idx = getattr(self, "container_index", None)
            if isinstance(idx, dict):
                meta = self.containers[name].get("meta") or {}
                idx[name] = {"id": name, "address": meta.get("address"), "type": self.containers[name].get("type", "container")}
        except Exception:
            pass

        try:
            if getattr(self, "visualizer", None):
                self.visualizer.log_event(name, "container_saved")
        except Exception:
            pass

        try:
            self._kg_emit("ucs_save_container", {"id": name}, tags=["ucs", "save"])
            self._mg_register("save", meta={"type": "ucs", "tags": ["ucs", "save"]})
        except Exception:
            pass

        return self.containers[name]

    def remove_container(self, container_id: str) -> Dict[str, Any]:
        if container_id not in self.containers:
            return {"ok": False, "reason": "not_found", "container_id": container_id}
        if container_id == DEFAULT_HUB_ID:
            return {"ok": False, "reason": "cannot_remove_hub", "container_id": container_id}

        container = self.containers[container_id]

        removed_atom_ids: List[str] = []
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
            pass

        removed_addresses: List[str] = []
        try:
            meta = (container.get("meta") or {}) if isinstance(container, dict) else {}
            addr = meta.get("address")
            if isinstance(addr, str) and self.address_index.get(addr) == container_id:
                del self.address_index[addr]
                removed_addresses.append(addr)

            for a, cid in list(self.address_index.items()):
                if cid == container_id and a not in removed_addresses:
                    del self.address_index[a]
                    removed_addresses.append(a)
        except Exception:
            pass

        try:
            for other_id, other in self.containers.items():
                if other_id == container_id:
                    continue
                wl = other.get("wormholes") if isinstance(other, dict) else None
                if isinstance(wl, list) and container_id in wl:
                    other["wormholes"] = [w for w in wl if w != container_id]
        except Exception:
            pass

        try:
            idx = getattr(self, "container_index", None)
            if isinstance(idx, dict) and container_id in idx:
                del idx[container_id]
        except Exception:
            pass

        del self.containers[container_id]

        if getattr(self, "active_container_name", None) == container_id:
            self.active_container_name = DEFAULT_HUB_ID if DEFAULT_HUB_ID in self.containers else None

        try:
            registry_unregister_container(container_id)
        except Exception:
            pass

        try:
            if getattr(self, "visualizer", None):
                self.visualizer.log_event(container_id, "container_removed")
        except Exception:
            pass

        try:
            self._kg_emit(
                "ucs_remove_container",
                {"id": container_id, "removed_atoms": len(removed_atom_ids), "removed_addresses": removed_addresses},
                tags=["ucs", "remove"],
            )
            self._mg_register("del", meta={"type": "ucs", "tags": ["ucs", "remove"]})
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
        return self.containers.get(name, {})

    def get_active_container(self) -> Dict[str, Any]:
        if self.active_container_name and self.active_container_name in self.containers:
            return self.containers[self.active_container_name]
        if self.containers:
            return next(iter(self.containers.values()))
        return {"id": "ucs_ephemeral", "glyph_grid": []}

    # ─────────────────────────────────────────────────────────────────────────
    # Broadcast
    # ─────────────────────────────────────────────────────────────────────────
    def broadcast(self, tag: str, payload: dict):
        try:
            logger.info(f"[📡 UCSRuntime.broadcast] {tag} -> {payload}")
            try:
                from backend.modules.sqi.sqi_event_bus import publish
                publish({"type": tag, "timestamp": time.time(), "payload": payload})
            except Exception as e:
                logger.debug(f"[UCSRuntime.broadcast] No SQI bridge: {e}")
        except Exception as e:
            logger.warning(f"[UCSRuntime.broadcast] failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Container registration (idempotent)
    # ─────────────────────────────────────────────────────────────────────────
    def register_container(self, container_name: str, container_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
        existing = self.containers.get(container_name, {}) or {}

        if container_data is None:
            container_data = {}
        else:
            container_data = normalize_container_dict(container_data)

        container_data.setdefault("id", container_name)
        container_data.setdefault("type", existing.get("type", "container"))

        merged = {**existing, **container_data}
        merged.setdefault("atoms", {})

        self.containers[container_name] = merged

        try:
            self._ensure_address_and_wormhole(container_name, merged)
        except Exception as e:
            print(f"[⚠️ register_container] Failed wormhole/address for '{container_name}': {e}")

        try:
            idx = getattr(self, "container_index", None)
            if isinstance(idx, dict):
                meta = merged.get("meta") or {}
                idx[container_name] = {"id": container_name, "address": meta.get("address"), "type": merged.get("type", "container")}
        except Exception as e:
            print(f"[⚠️ register_container] Failed container_index update for '{container_name}': {e}")

        try:
            if getattr(self, "visualizer", None):
                cid = merged.get("id") or merged.get("name") or container_name
                cname = merged.get("name") or container_name
                self._ghx_register_once(cid, cname)
        except Exception as e:
            print(f"[⚠️ register_container] GHX visualizer register failed for '{container_name}': {e}")

        try:
            self._kg_emit("ucs_register_container", {"id": container_name}, tags=["ucs", "register"])
            self._mg_register("reg", meta={"type": "ucs", "tags": ["ucs", "register"]})
        except Exception:
            pass

        print(f"[✅ UCSRuntime] Registered container: {container_name}")
        return merged

    def resolve_atom(self, key: str) -> Optional[str]:
        if not key:
            return None
        if key in self.atom_index:
            return key
        hit = self.address_index.get(key)
        if hit:
            return hit
        try:
            return resolve_by_address(key)
        except Exception:
            return None

    def debug_state(self) -> Dict[str, Any]:
        try:
            containers_list = list(getattr(self, "container_index", {}).keys())
            if not containers_list:
                containers_list = list(getattr(self, "containers", {}).keys())
        except Exception:
            containers_list = list(getattr(self, "containers", {}).keys())

        active = getattr(self, "active_container_name", None) or getattr(self, "active_container", None)
        local_addrs = list(getattr(self, "address_index", {}).keys())

        # Registry addresses (global) — supports list[str] OR list[tuple[cid, addr]]
        try:
            raw = registry_list_addresses()  # may be ["ucs://..", ...] OR [("id","ucs://.."), ...]
            registry_addrs = []
            if raw:
                first = raw[0]
                if isinstance(first, (tuple, list)) and len(first) >= 2:
                    registry_addrs = [addr for (_cid, addr, *_) in raw]
                else:
                    registry_addrs = list(raw)
        except Exception:
            registry_addrs = []

        atom_idx = getattr(self, "atom_index", {}) or {}

        return {
            "containers": containers_list,
            "active_container": active,
            "atom_index_count": len(atom_idx),
            "atom_ids": list(atom_idx.keys()),
            "addresses": sorted(set(local_addrs + registry_addrs)),
        }

    def get_atoms(self, selector: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        atom_index = getattr(self, "atom_index", None) or {}
        if not atom_index:
            return []

        caps_req = set((selector or {}).get("caps", []))
        tags_req = set((selector or {}).get("tags", []))
        nodes_req = set((selector or {}).get("nodes", []))

        results: List[Dict[str, Any]] = []
        for entry in atom_index.values():
            atom = entry
            if isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[1], dict):
                atom = entry[1]
            if not isinstance(atom, dict):
                continue

            if caps_req and not caps_req.intersection(atom.get("caps", [])):
                continue
            if tags_req and not tags_req.intersection(atom.get("tags", [])):
                continue
            if nodes_req and not nodes_req.intersection(atom.get("nodes", [])):
                continue
            results.append(atom)

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Runtime Execution
    # ─────────────────────────────────────────────────────────────────────────
    def run_container(self, name: str):
        if name not in self.containers:
            raise ValueError(f"Container '{name}' not loaded.")
        container = self.containers[name]
        print(f"🚀 Running container: {name}")

        self.soul_law.validate_access(container)

        for glyph in container.get("glyphs", []):
            if glyph in self.trigger_map.map:
                event = self.trigger_map.map[glyph]
                self.emit_event(event, container)

        self.visualizer.highlight(name)
        try:
            self._kg_emit("ucs_highlight", {"id": name}, tags=["ucs", "viz"])
        except Exception:
            pass
        self.active_container_name = name

    def run_all(self):
        for name in list(self.containers.keys()):
            self.run_container(name)
            time.sleep(0.5)

    def emit_event(self, event_name: str, container: dict):
        cname = (container.get("name") or container.get("id") or "<?>") if isinstance(container, dict) else "<?>"
        print(f"⚡ Emitting event: {event_name} from {cname}")
        sqi = getattr(self, "sqi", None)
        if sqi:
            try:
                sqi.emit(event_name, payload={"container": container})
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # Legacy Expansion / Collapse
    # ─────────────────────────────────────────────────────────────────────────
    def expand_container(self, name: str):
        c = self.get_container(name)
        c["state"] = "expanded"
        self.save_container(name, c)
        return c

    def collapse_container(self, name: str):
        c = self.get_container(name)
        c["state"] = "collapsed"
        self.save_container(name, c)
        return c

    def embed_glyph_block_into_container(self, name: str, glyph_block: Any):
        c = self.get_container(name)
        c.setdefault("glyphs", []).append(glyph_block)
        self.save_container(name, c)


# ─────────────────────────────────────────────────────────────────────────────
# ✅ Singleton Initialization + Safe Legacy Aliases
# ─────────────────────────────────────────────────────────────────────────────
def broadcast(tag: str, payload: dict):
    """Module-level shim: always uses the UCS singleton."""
    return get_ucs_runtime().broadcast(tag, payload)


_ucs_singleton: Optional[UCSRuntime] = None


def get_ucs_runtime() -> UCSRuntime:
    global _ucs_singleton
    if _ucs_singleton is None:
        _ucs_singleton = UCSRuntime()
        # ensure a safe sqi object exists (prevents None.emit crashes)
        if getattr(_ucs_singleton, "sqi", None) is None:
            _ucs_singleton.sqi = _SQIStub()
    return _ucs_singleton


ucs_runtime = get_ucs_runtime()


def _alias(name: str):
    """Return bound UCSRuntime method if it exists, else raise AttributeError on call."""
    attr = getattr(ucs_runtime, name, None)
    if callable(attr):
        return attr

    def _missing(*args, **kwargs):
        raise NotImplementedError(f"{name} is not implemented in UCSRuntime")
    return _missing


load_dc_container = _alias("load_container_from_path")
load_container_from_path = _alias("load_container_from_path")
load_container = _alias("load_container")
expand_container = _alias("expand_container")
collapse_container = _alias("collapse_container")
embed_glyph_block_into_container = _alias("embed_glyph_block_into_container")

__all__ = [
    "UCSRuntime",
    "ucs_runtime",
    "get_ucs_runtime",
    "broadcast",
    "load_dc_container",
    "load_container_from_path",
    "load_container",
    "expand_container",
    "collapse_container",
    "embed_glyph_block_into_container",
]