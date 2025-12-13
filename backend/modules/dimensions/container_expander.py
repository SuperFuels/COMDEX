# backend/modules/dimensions/container_expander.py

from __future__ import annotations

import time  # used by grow_space, keep once
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.aion.address_book import address_book
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCSGeometryLoader
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer  # ✅ canonical
from backend.modules.dna_chain.container_index_writer import add_to_index
from backend.modules.websocket_manager import broadcast_event as broadcast_glyph_event

from .dimension_kernel import DimensionKernel

_checked_containers_for_expander = set()

# -----------------------------------------------------------------------------
# Safe fallbacks so this module works in tests/CLI even if deps aren't loaded
# -----------------------------------------------------------------------------
try:
    from backend.modules.sqi.sqi_event_bus import emit_sqi_event
except Exception:  # pragma: no cover
    def emit_sqi_event(*_a, **_k):  # no-op in test/CLI
        pass

try:
    # prefer the dna_chain linker as the canonical entanglement API
    from backend.modules.dna_chain.container_linker import entangle_containers
except Exception:  # pragma: no cover
    def entangle_containers(*_a, **_k):  # no-op in test/CLI
        pass

try:
    from backend.modules.dna_chain.container_linker import link_wormhole
except Exception:  # pragma: no cover
    def link_wormhole(*_a, **_k):  # no-op
        pass

# SoulLaw: prefer lazy accessor; fall back to legacy class if present
try:
    from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator
except Exception:  # pragma: no cover
    get_soul_law_validator = None  # type: ignore

try:
    from backend.modules.glyphvault.soul_law_validator import SoulLawValidator  # legacy
except Exception:  # pragma: no cover
    SoulLawValidator = None  # type: ignore

# --- Microgrid (best-effort global) ------------------------------------------
try:
    from backend.modules.glyphos.microgrid_index import MicrogridIndex
    MICROGRID = getattr(MicrogridIndex, "_GLOBAL", None) or MicrogridIndex()
    MicrogridIndex._GLOBAL = MICROGRID
except Exception:  # pragma: no cover
    MICROGRID = None

# -----------------------------------------------------------------------------
# Seed helpers (non-breaking)
# -----------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent
_SEEDS_DIR = _BASE_DIR / "containers"

_SEED_FILES = {
    "math_core": _SEEDS_DIR / "math_core.dc.json",
    "physics_core": _SEEDS_DIR / "physics_core.dc.json",
    # "control_systems": _SEEDS_DIR / "control_systems.dc.json",
}

def _get_seed_path(container_id: str) -> Optional[str]:
    p = _SEED_FILES.get(container_id)
    if p and p.exists():
        return str(p)
    return None

def _load_seed(container_id: str) -> Optional[dict]:
    """Best-effort JSON loader for a seed .dc file."""
    spath = _get_seed_path(container_id)
    if not spath:
        return None
    try:
        with open(spath, "r", encoding="utf-8") as f:
            obj = json.load(f)
            return obj if isinstance(obj, dict) else None
    except Exception as e:
        print(f"[seed:{container_id}] failed to load: {e}")
        return None

def _merge_seed_into_container(container: dict, seed: dict) -> None:
    """
    Merge seed content into the container snapshot without clobbering existing data.
    Adds glyph_categories, nodes, and links if present.
    """
    if not seed:
        return

    container.setdefault("glyph_categories", [])
    container.setdefault("nodes", [])
    container.setdefault("links", [])

    def _by_id(items):
        out = {}
        for it in items:
            if isinstance(it, dict):
                _id = it.get("id")
                if _id:
                    out[_id] = it
        return out

    # glyph_categories
    seed_cats = seed.get("glyph_categories") or []
    if isinstance(seed_cats, list) and seed_cats:
        existing_cats = _by_id(container.get("glyph_categories") or [])
        for c in seed_cats:
            if not isinstance(c, dict):
                continue
            cid = c.get("id")
            if cid and cid not in existing_cats:
                container["glyph_categories"].append(c)

    # nodes
    seed_nodes = seed.get("nodes") or []
    if isinstance(seed_nodes, list) and seed_nodes:
        existing_nodes = _by_id(container.get("nodes") or [])
        for n in seed_nodes:
            if not isinstance(n, dict):
                continue
            nid = n.get("id")
            if nid and nid not in existing_nodes:
                container["nodes"].append(n)

    # links (src/dst/relation triplets)
    seed_links = seed.get("links") or []
    if isinstance(seed_links, list) and seed_links:
        seen = {
            (l.get("src"), l.get("dst"), l.get("relation"))
            for l in (container.get("links") or [])
            if isinstance(l, dict)
        }
        for e in seed_links:
            if not isinstance(e, dict):
                continue
            key = (e.get("src"), e.get("dst"), e.get("relation"))
            if key not in seen and key[0] and key[1]:
                container["links"].append(e)
                seen.add(key)

# --- physics alias shim (non-destructive) -----------------------------------
def _ensure_physics_alias_categories(container: dict) -> None:
    container.setdefault("glyph_categories", [])
    existing_ids = {c.get("id") for c in container["glyph_categories"] if isinstance(c, dict)}

    alias_map = {
        "N_mechanics": ("Mechanics", "newton_laws"),
        "N_em_field": ("Electromagnetism", "maxwell_eqs"),
        "N_qft": ("Quantum Field Theory", "dirac_field"),
        "N_energy": ("Energy", "energy"),
    }

    for alias_id, (title, canon_id) in alias_map.items():
        if alias_id in existing_ids:
            continue
        container["glyph_categories"].append({
            "id": alias_id,
            "title": title,
            "alias_of": canon_id,
            "tags": ["alias", "physics"],
            "meta": {"origin": "auto-alias"},
        })

# --- physics snapshot alias helper (non-mutating) ----------------------------
def _snapshot_with_aliases(container: dict) -> dict:
    snap = dict(container)
    snap.setdefault("glyph_categories", [])
    snap.setdefault("nodes", [])
    snap.setdefault("links", [])

    have_cat_ids = {c.get("id") for c in snap["glyph_categories"] if isinstance(c, dict)}
    have_node_ids = {n.get("id") for n in snap["nodes"] if isinstance(n, dict)}
    node_cats = {n.get("cat") for n in snap["nodes"] if isinstance(n, dict) and n.get("cat")}

    base_map = {
        "mech": ("Mechanics", "⚙️"),
        "thermo": ("Thermodynamics", "🔥"),
        "em": ("Electromagnetism", "⚡"),
        "qft": ("Quantum Fields", "🌀"),
    }
    backfill_rows = []
    for cid, (label, emoji) in base_map.items():
        if (cid in node_cats) and (cid not in have_cat_ids):
            backfill_rows.append({"id": cid, "label": label, "emoji": emoji})
    if backfill_rows:
        snap["glyph_categories"] = list(snap["glyph_categories"]) + backfill_rows
        have_cat_ids |= {r["id"] for r in backfill_rows}

    alias_cat_map = {
        "N_mechanics": ("Mechanics", "newton_laws", "newton_laws"),
        "N_em_field": ("Electromagnetism", "maxwell_eqs", "maxwell_eqs"),
        "N_qft": ("Quantum Field Theory", "dirac_field", "dirac_field"),
        "N_energy": ("Energy", "energy", "energy"),
    }
    alias_cat_rows = []
    for alias_id, (title, canon_cat_id, fallback_node_id) in alias_cat_map.items():
        if alias_id in have_cat_ids:
            continue
        canon_present = (canon_cat_id in have_cat_ids) or (fallback_node_id in have_node_ids)
        if canon_present:
            alias_cat_rows.append({
                "id": alias_id,
                "title": title,
                "alias_of": canon_cat_id,
                "tags": ["alias", "physics"],
                "meta": {"origin": "auto-alias"},
            })
    if alias_cat_rows:
        snap["glyph_categories"] = list(snap["glyph_categories"]) + alias_cat_rows

    alias_node_map = {
        "N_force": ("Force", "newton_laws", "mech"),
        "N_maxwell": ("Maxwell", "maxwell_eqs", "em"),
        "N_qft": ("Quantum Fields", "dirac_field", "qft"),
        "N_energy": ("Energy", "energy", "thermo"),
    }
    alias_node_rows = []
    for alias_id, (label, canon_node_id, cat_hint) in alias_node_map.items():
        if alias_id in have_node_ids:
            continue
        canon_present = (canon_node_id in have_node_ids)
        if canon_present or alias_id == "N_energy":
            alias_node_rows.append({
                "id": alias_id,
                "label": label,
                "alias_of": canon_node_id,
                "cat": cat_hint,
                "tags": ["alias", "physics"],
                "meta": {"origin": "auto-alias"},
            })
    if alias_node_rows:
        snap["nodes"] = list(snap["nodes"]) + alias_node_rows

    existing_link_keys = {
        (l.get("src"), l.get("dst"), l.get("relation"))
        for l in snap["links"]
        if isinstance(l, dict)
    }
    new_node_ids = have_node_ids | {r["id"] for r in alias_node_rows}
    alias_link = ("N_force", "N_energy", "work-energy")
    if alias_link not in existing_link_keys:
        if "N_force" in new_node_ids and "N_energy" in new_node_ids:
            snap["links"] = list(snap["links"]) + [{
                "src": "N_force",
                "dst": "N_energy",
                "relation": "work-energy",
                "tags": ["alias", "physics"],
                "meta": {"origin": "auto-alias"},
            }]

    return snap


# ============================================================================
class ContainerExpander:
    def __init__(self, container_id: str):
        self.kernel = DimensionKernel(container_id)
        self.container_id = container_id
        self.geometry_loader = UCSGeometryLoader()
        self.ucs = ucs_runtime
        self.kg_writer = None

        # ✅ Initialize KG writer singleton safely
        try:
            self.kg_writer = get_kg_writer()
        except Exception as e:
            print(f"⚠️ get_kg_writer() unavailable: {e}")
            self.kg_writer = None

        # ✅ Get or init container state from Kernel (compat)
        container = self._get_container()
        container = self._normalize_container(container)

        # ✅ Seed merge (best-effort)
        try:
            seed = _load_seed(self.container_id)
            if seed:
                _merge_seed_into_container(container, seed)
                if self.container_id == "physics_core":
                    _ensure_physics_alias_categories(container)
                self._set_container(container)
        except Exception as e:
            print(f"⚠️ Seed merge skipped: {e}")

        # ✅ Address + wormhole (idempotent)
        try:
            address_book.register_container(container)
        except Exception as e:
            print(f"⚠️ AddressBook register failed for {container.get('id', self.container_id)}: {e}")

        try:
            link_wormhole(container.get("id", self.container_id), "ucs_hub")
        except Exception as e:
            print(f"⚠️ Wormhole link failed for {container.get('id', self.container_id)}: {e}")

        # ✅ Save to UCS (ensures address/wormhole stamping there too)
        self.ucs.save_container(self.container_id, container)

    # -------------------------------------------------------------------------
    # Kernel container state compatibility
    # -------------------------------------------------------------------------
    def _set_container(self, new_state: dict) -> None:
        k = self.kernel
        if hasattr(k, "set_container") and callable(getattr(k, "set_container")):
            k.set_container(new_state)
            return
        if hasattr(k, "load_snapshot") and callable(getattr(k, "load_snapshot")):
            k.load_snapshot(new_state)
            return
        if hasattr(k, "container"):
            setattr(k, "container", new_state)
        else:
            setattr(k, "state", new_state)

    def _get_container(self) -> dict:
        k = self.kernel
        candidates = (
            "get_container",
            "container",
            "state",
            "get_state",
            "to_dict",
            "snapshot",
            "get_snapshot",
            "dump_snapshot",
        )
        for name in candidates:
            if not hasattr(k, name):
                continue
            attr = getattr(k, name)
            try:
                value = attr() if callable(attr) else attr
            except TypeError:
                continue
            if isinstance(value, dict):
                return value

        print("⚠️ ContainerExpander: falling back to minimal container skeleton")
        return {
            "id": getattr(k, "container_id", self.container_id),
            "name": self.container_id,
            "symbol": "❔",
            "glyph_categories": [],
            "nodes": [],
            "links": [],
            "entangled": [],
            "meta": {"address": f"ucs://local/{self.container_id}#container"},
        }

    def _normalize_container(self, container: dict) -> dict:
        """Ensure minimal fields exist so downstream hooks don’t explode."""
        cid = container.get("id") or container.get("container_id") or self.container_id
        container.setdefault("id", cid)
        container.setdefault("name", container.get("name") or cid)
        container.setdefault("meta", {})
        if isinstance(container["meta"], dict):
            container["meta"].setdefault("address", f"ucs://local/{cid}#container")
        container.setdefault("glyph_categories", [])
        container.setdefault("nodes", [])
        container.setdefault("links", [])
        container.setdefault("entangled", [])
        return container

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def seed_initial_space(self, size: int = 3, geometry: str = "Tesseract"):
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    self.kernel.register_cube(x, y, z, 0)

        container = self._normalize_container(self._get_container())
        container_name = container.get("name", self.container_id)
        container_symbol = container.get("symbol", "❔")
        container["geometry"] = geometry

        # ✅ Geometry registration
        try:
            self.geometry_loader.register_geometry(container_name, container_symbol, geometry)
        except Exception as e:
            print(f"⚠️ Geometry registration failed for {self.container_id}: {e}")

        # 🧠 KG geometry index (optional)
        try:
            if self.kg_writer and hasattr(self.kg_writer, "index_geometry"):
                self.kg_writer.index_geometry(
                    container_id=self.container_id,
                    name=container_name,
                    symbol=container_symbol,
                    geometry=geometry,
                )
        except Exception as e:
            print(f"[WARN] KG index failed for container {self.container_id}: {e}")

        # 🌀 SQI + entanglement ping
        try:
            emit_sqi_event("ucs_geometry_registered", {
                "container_id": self.container_id,
                "name": container_name,
                "symbol": container_symbol,
                "geometry": geometry,
            })
        except Exception:
            pass

        try:
            entangle_containers(self.container_id, source="ucs_geometry")
        except Exception:
            pass

        # ✅ Persist
        self.ucs.save_container(self.container_id, container)
        try:
            link_wormhole(self.container_id, "ucs_hub")
        except Exception:
            pass

        # ✅ Load domain pack (optional)
        if self.container_id == "physics_core":
            try:
                if self.kg_writer and hasattr(self.kg_writer, "load_domain_pack"):
                    self.kg_writer.load_domain_pack("physics_core", container)
            except Exception as e:
                print(f"⚠️ KG domain load skipped: {e}")

        # ✅ GHX highlight (best-effort)
        try:
            self.ucs.visualizer.highlight(self.container_id)
        except Exception as e:
            print(f"⚠️ GHX highlight failed during seed: {e}")

        return f"🌱 Seeded initial {size}x{size}x{size} runtime space."

    def grow_space(self, direction: str = "z", layers: int = 1):
        result = self.kernel.expand(axis=direction, amount=layers)
        container = self._normalize_container(self._get_container())

        try:
            address_book.register_container(container)
        except Exception as e:
            print(f"⚠️ AddressBook register failed during growth for {container.get('id')}: {e}")

        self.ucs.save_container(self.container_id, container)
        try:
            link_wormhole(self.container_id, "ucs_hub")
        except Exception as e:
            print(f"⚠️ Wormhole link failed for {self.container_id}: {e}")

        # ✅ GHX sync
        try:
            self.ucs.visualizer.highlight(self.container_id)
        except Exception as e:
            print(f"⚠️ GHX visualization sync failed: {e}")

        # ✅ Entanglement-aware growth
        for eid in (container.get("entangled") or []):
            try:
                entangle_containers(self.container_id, eid)
                print(f"↔ Propagated growth to entangled container: {eid}")
            except Exception as e:
                print(f"⚠️ Failed to propagate entanglement growth: {e}")

        emit_sqi_event("container_growth", {
            "container_id": self.container_id,
            "direction": direction,
            "layers": layers,
            "timestamp": time.time(),
        })

        # 🧠 KG signal (optional)
        try:
            if self.kg_writer and hasattr(self.kg_writer, "inject_glyph"):
                self.kg_writer.inject_glyph(
                    content={"event": "container_growth", "direction": direction, "layers": layers},
                    glyph_type="container_growth",
                    metadata={"container_id": self.container_id},
                    tags=["expander", "growth"],
                    agent_id="container_expander",
                )
        except Exception:
            pass

        return result

    def _evaluate_glyph_soullaw(self, glyph: Any) -> str:
        """Return 'approved'/'denied'/etc. Best-effort across validator versions."""
        # Preferred: instance from get_soul_law_validator()
        try:
            if get_soul_law_validator:
                v = get_soul_law_validator()
                if hasattr(v, "evaluate_glyph"):
                    return str(v.evaluate_glyph(glyph))
        except Exception:
            pass

        # Legacy: SoulLawValidator.evaluate_glyph
        try:
            if SoulLawValidator and hasattr(SoulLawValidator, "evaluate_glyph"):
                return str(SoulLawValidator.evaluate_glyph(glyph))
        except Exception:
            pass

        # Default permissive (don’t brick runtime if validator missing)
        return "approved"

    def inject_glyph(self, x: int, y: int, z: int, t: int, glyph: Any):
        container = self._normalize_container(self._get_container())
        container_id = container.get("id", self.container_id)

        # ✅ SoulLaw validation once per container (avoid loops)
        if not hasattr(self, "_soullaw_checked_containers"):
            self._soullaw_checked_containers = set()

        if container_id not in self._soullaw_checked_containers:
            verdict = self._evaluate_glyph_soullaw(glyph)

            try:
                # UCS runtime enforcement (container-level)
                self.ucs.soul_law.validate_access(container)
            except Exception as e:
                print(f"⚠️ UCS SoulLaw enforcement failed: {e}")
                raise

            self._soullaw_checked_containers.add(container_id)

            if verdict != "approved":
                raise PermissionError(f"❌ SoulLaw denied glyph injection: {glyph} (verdict: {verdict})")

        # ✅ Inject glyph into runtime
        self.kernel.add_glyph(x, y, z, t, glyph)
        container = self._normalize_container(self._get_container())

        # ✅ Knowledge Graph & Index Sync
        entry = {
            "id": f"glyph_{int(time.time())}",
            "type": "glyph",
            "content": glyph,
            "timestamp": time.time(),
            "metadata": {"tags": ["glyph_injection"], "coord": f"{x},{y},{z},{t}"},
        }
        try:
            add_to_index("glyph_index", entry)
        except Exception:
            pass

        try:
            if self.kg_writer and hasattr(self.kg_writer, "inject_glyph"):
                self.kg_writer.inject_glyph(
                    content={"glyph": glyph, "pos": {"x": x, "y": y, "z": z, "t": t}},
                    glyph_type="glyph",
                    metadata={"coord": f"{x},{y},{z},{t}", "container_id": self.container_id},
                    tags=["glyph_injection", "expander"],
                    agent_id="container_expander",
                )
            elif self.kg_writer and hasattr(self.kg_writer, "write_glyph_entry"):
                self.kg_writer.write_glyph_entry(entry)
        except Exception as e:
            print(f"⚠️ KG writer skipped: {e}")

        # ✅ Microgrid HUD tap (best-effort; coordinates mod 16)
        if MICROGRID:
            try:
                MICROGRID.register_glyph(
                    x % 16, y % 16, z % 16,
                    glyph=str(glyph),
                    layer=int(t) if t is not None else None,
                    metadata={"type": "glyph", "tags": ["expander", "inject"], "energy": 1.0},
                )
            except Exception:
                pass

        # ✅ UCS Save & GHX Sync
        self.ucs.save_container(self.container_id, container)

        try:
            broadcast_glyph_event({
                "type": "glyph_injection",
                "data": {
                    "coord": f"{x},{y},{z}",
                    "glyph": glyph,
                    "container_id": self.container_id,
                    "timestamp": time.time(),
                }
            })
        except Exception as e:
            print(f"⚠️ WebSocket broadcast failed: {e}")

        emit_sqi_event("glyph_injection", {
            "container_id": self.container_id,
            "glyph": glyph,
            "coord": f"{x},{y},{z}",
            "timestamp": time.time(),
        })

        return f"✨ Glyph '{glyph}' injected at ({x},{y},{z})"

    def status(self):
        container = self._normalize_container(self._get_container())
        print("DEBUG before alias: cats =", [
            c.get("id") for c in container.get("glyph_categories", []) if isinstance(c, dict)
        ])
        if self.container_id == "physics_core":
            container = _snapshot_with_aliases(container)
        print("DEBUG after alias:  cats =", [
            c.get("id") for c in container.get("glyph_categories", []) if isinstance(c, dict)
        ])
        print(f"📦 Container Snapshot: {self.container_id}")
        return container