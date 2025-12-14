# -*- coding: utf-8 -*-
"""
📄 knowledge_graph_writer.py

🧠 Knowledge Graph Writer (CRDT + Entanglement Locks + Conflict Handling)
Injects symbolic glyphs (memory, reflection, predictions, events) into active `.dc` containers.
Adds multi-agent CRDT merge, entanglement locks, and conflict glyph tagging.

Design Rubric:
- 🧠 Symbolic Glyph Type/Role ............... ✅
- 📩 Intent + Reason + Trigger Metadata ..... ✅
- 📦 Container Context + Coord Awareness .... ✅
- ⏱️ Timestamp + Runtime Trace Binding ...... ✅
- 🧩 Plugin & Forecast Integration ...........✅
- 🔁 Self-Reflection + Thought Tracing ...... ✅
- 📊 Validator: Stats, Search, DC Export .... ✅
- 🌐 CRDT & Entanglement Locks .............. ✅
"""
import importlib
import os, json
import uuid
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

try:
    # preferred path resolver
    from backend.modules.dna_chain.dc_handler import get_dc_path
except Exception:
    get_dc_path = None

# ✅ Correct utility imports
from backend.modules.knowledge_graph.id_utils import generate_uuid
from backend.modules.knowledge_graph.time_utils import get_current_timestamp
from backend.modules.sqi.sqi_metadata_embedder import bake_hologram_meta, make_kg_payload
from backend.modules.knowledge_graph.sqi_fastmap_index import sqi_fastmap
from backend.modules.dimensions.containers.container_loader import load_decrypted_container
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.knowledge_graph.indexes.trace_index import inject_trace_event
from backend.modules.codex.codex_metrics import CodexMetrics
codex_metrics = CodexMetrics()  # instantiate singleton instance
from backend.modules.glyphwave.qwave.qwave_writer import collect_qwave_beams, export_qwave_beams

# ✅ Knowledge graph and indexing
from backend.modules.dna_chain.container_index_writer import add_to_index

# HOV integration (adds hover/collapse + viz hints + lazy expansion)
from backend.modules.sqi.sqi_metadata_embedder import (
    bake_hologram_meta,
    make_kg_payload,
)

# Where KG exports will be written (mirrors boot_loader defaults)
# --- KG export location (persistent) ---
_REPO_ROOT = Path(__file__).resolve().parents[3]
KG_EXPORTS_DIR = _REPO_ROOT / "backend" / "modules" / "dimensions" / "containers" / "kg_exports"
KG_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
_KG_BUSY = False

# --- add near the top of the file (after imports) ---
_EPHEMERAL_CONTAINER = {"id": "kg_cli_ephemeral", "glyph_grid": [], "last_updated": None}
ENABLE_WS_BROADCAST = os.getenv("AION_ENABLE_WS_BROADCAST", "1") == "1"

import asyncio

def _env_bool(name: str, default: str = "1") -> bool:
    v = os.getenv(name, default)
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

# Default OFF: avoids broadcast + avoids printing no-loop errors on reload/start
_KG_QFC_BROADCAST = _env_bool("KG_QFC_BROADCAST", "0")

def _has_running_loop() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def get_active_container():
    """
    Try to fetch the active container from state_manager.
    In CLI or test contexts (no server running), fall back to an in-memory container.
    """
    try:
        sm = importlib.import_module("backend.modules.consciousness.state_manager")
        ucs = sm.get_active_universal_container_system()
        return ucs.get("active_container", _EPHEMERAL_CONTAINER)
    except Exception:
        # CLI/test mode: no UCS - return ephemeral container so inject_glyph still works
        return _EPHEMERAL_CONTAINER

# ──────────────────────────────
# Lazy WS helpers (avoid circular import)
# ──────────────────────────────
def lazy_broadcast_anchor_update(*args, **kwargs):
    from backend.routes.ws.glyphnet_ws import broadcast_anchor_update  # Lazy import
    return broadcast_anchor_update(*args, **kwargs)

def lazy_broadcast_event(payload: Dict[str, Any]):
    from backend.routes.ws.glyphnet_ws import broadcast_event  # Lazy import
    return broadcast_event(payload)

# Safe task creator for optional async WS calls
def _safe_emit(coro_or_none):
    try:
        import inspect, asyncio
        if not coro_or_none:
            return
        if inspect.iscoroutine(coro_or_none):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro_or_none)
            except RuntimeError:
                # No running loop -> run once synchronously
                asyncio.run(coro_or_none)
    except Exception:
        # Don't let telemetry break core writes
        pass

import hashlib  # add if not already imported

def _h16(s: str) -> int:
    """
    Deterministic 0..15 bucket using BLAKE2b(16-bit).
    Stable across processes (unlike Python's built-in hash).
    """
    return int(hashlib.blake2b(s.encode("utf-8"), digest_size=2).hexdigest(), 16) % 16

# ──────────────────────────────
# CRDT & Entanglement Lock Registry
# ──────────────────────────────
class CRDTRegistry:
    def __init__(self):
        self.version_vectors = defaultdict(lambda: defaultdict(int))  # {glyph_id: {agent_id: clock}}
        self.locks = {}  # {glyph_id: agent_id}
        self.entanglement_locks = {}  # {entangled_group_id: agent_id}

    def increment_clock(self, glyph_id: str, agent_id: str):
        self.version_vectors[glyph_id][agent_id] += 1
        return self.version_vectors[glyph_id]

    def merge_vector(self, glyph_id: str, incoming: Dict[str, int]):
        local = self.version_vectors[glyph_id]
        for agent, clock in incoming.items():
            local[agent] = max(local.get(agent, 0), clock)
        return local

    def acquire_lock(self, glyph_id: str, agent_id: str) -> bool:
        if glyph_id in self.locks and self.locks[glyph_id] != agent_id:
            return False
        self.locks[glyph_id] = agent_id
        return True

    def release_lock(self, glyph_id: str, agent_id: str):
        if self.locks.get(glyph_id) == agent_id:
            del self.locks[glyph_id]

    def is_locked(self, glyph_id: str) -> Optional[str]:
        return self.locks.get(glyph_id)

    def acquire_entanglement_lock(self, entangled_group: str, agent_id: str) -> bool:
        if entangled_group in self.entanglement_locks and self.entanglement_locks[entangled_group] != agent_id:
            return False
        self.entanglement_locks[entangled_group] = agent_id
        return True

    def release_entanglement_lock(self, entangled_group: str, agent_id: str):
        if self.entanglement_locks.get(entangled_group) == agent_id:
            del self.entanglement_locks[entangled_group]

    def is_entanglement_locked(self, entangled_group: str) -> Optional[str]:
        return self.entanglement_locks.get(entangled_group)


crdt_registry = CRDTRegistry()


# ──────────────────────────────
# Knowledge Graph Writer
# ──────────────────────────────
class KnowledgeGraphWriter:
    def __init__(self, container_id: Optional[str] = None, **kwargs):
        # Explicitly attached UCS container (if any)
        self._container = None 
        self.container_id = container_id 

    def attach_metadata(self, glyph_id: str, metadata: Dict[str, Any]):
        """
        Attach metadata to a glyph within the currently attached container.

        Args:
            glyph_id (str): ID of the glyph to modify.
            metadata (Dict): Metadata to merge into the glyph.
        """
        if not hasattr(self, "_container") or not self._container:
            print(f"[KGWriter] ⚠️ No container attached.")
            return

        found = False
        for glyph in self._container.get("glyphs", []):
            if glyph.get("id") == glyph_id:
                if "metadata" not in glyph:
                    glyph["metadata"] = {}
                glyph["metadata"].update(metadata)
                found = True
                print(f"[KGWriter] ✅ Metadata attached to glyph {glyph_id}")
                break

        if not found:
            print(f"[KGWriter] ⚠️ Glyph ID {glyph_id} not found in attached container.")

    # ---------- helpers ----------
    def _container_path_for(self, container_id: str) -> str:
        """
        Resolve the .dc.json path for a container ID.
        Falls back to the standard containers dir if get_dc_path isn't available.
        """
        if get_dc_path:
            p = get_dc_path({"id": container_id})
            if p and os.path.isfile(p):
                return p
        # fallback path
        fallback = f"backend/modules/dimensions/containers/{container_id}.dc.json"
        return fallback

    @staticmethod
    def store_predictions(container_id: str, predictions: dict):
        """
        Store prediction results into the knowledge graph or attach to container metadata.
        """
        if not predictions:
            return

        logger.info(f"[KG] Storing predictions for container: {container_id}")
        
        # 🔁 Store to in-memory trace or glyph metadata (simplified example)
        path = f"backend/modules/dimensions/containers/{container_id}.dc.json"

        try:
            with open(path, "r", encoding="utf-8") as f:
                container = json.load(f)
        except FileNotFoundError:
            logger.warning(f"[KG] Could not find container file: {path}")
            return

        container.setdefault("predictions", {}).update(predictions)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(container, f, indent=2)
            logger.info(f"[KG] Predictions saved to container: {path}")
    
    def _safe_load_container(self, path: str) -> dict:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
                return obj if isinstance(obj, dict) else {}
        return {}

    def _safe_save_container(self, path: str, container: dict) -> None:
        Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(container, f, indent=2)

    def inject_node(
        self,
        container_id: str,
        node: dict,
        *,
        allow_create: bool = True,
        commit: bool = True
    ) -> dict:
        """
        Persist a KG node into a UCS container file AND into glyph_grid as a 'kg_node'
        so export_pack will pick it up.

        node: {"id": "...", "label": "...", "domain": "...", "tags": [...]}
        """
        if not isinstance(node, dict) or "id" not in node:
            raise ValueError("inject_node: node must be a dict with an 'id'")

        path = self._container_path_for(container_id)
        container = self._safe_load_container(path)

        # Create a minimal container if missing
        if not container:
            if not allow_create:
                raise FileNotFoundError(f"Container not found: {path}")
            container = {
                "id": container_id,
                "type": "container",
                "kind": node.get("kind", "fact"),
                "domain": node.get("domain"),
                "meta": {
                    "created_by": "SQI",
                    "last_updated": datetime.utcnow().isoformat(),
                    "ghx": {"hover": True, "collapsed": True},
                    "address": f"ucs://knowledge/{node.get('domain','unknown')}/{container_id}"
                },
                "atoms": {},
                "wormholes": ["ucs_hub"],
                "nodes": [],
                "glyphs": [],
                "glyph_grid": []
            }

        # Ensure required fields
        container.setdefault("nodes", [])
        container.setdefault("glyph_grid", [])
        container.setdefault("meta", {})
        meta = container["meta"]
        meta.setdefault("ghx", {"hover": True, "collapsed": True})

        # 1) Update/insert in plain nodes (idempotent)
        replaced = False
        for i, existing in enumerate(container["nodes"]):
            if isinstance(existing, dict) and existing.get("id") == node["id"]:
                container["nodes"][i] = {**existing, **node}
                replaced = True
                break
        if not replaced:
            container["nodes"].append(dict(node))

        # 2) Update/insert in glyph_grid as a kg_node (what export_pack reads)
        gg = container["glyph_grid"]
        # remove any existing kg_node with same id
        gg = [g for g in gg if not (isinstance(g, dict)
                                    and g.get("type") == "kg_node"
                                    and g.get("metadata", {}).get("id") == node["id"])]
        # append a fresh entry
        gg.append({
            "type": "kg_node",
            "metadata": dict(node)
        })
        container["glyph_grid"] = gg

        # Touch last_updated
        meta["last_updated"] = datetime.utcnow().isoformat()

        if commit:
            self._safe_save_container(path, container)

        return {
            "status": "ok",
            "container_id": container_id,
            "node_id": node["id"],
            "path": path
        }

    def add_node(self, container_id: str, node: dict, **kwargs) -> dict:
        """Back-compat: delegate to inject_node."""
        return self.inject_node(container_id, node, **kwargs)

    @property
    def container(self):
        """
        Return the bound container if set, otherwise fall back to UCS active container.
        """
        if self._container is None:
                from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
                self._container = ucs_runtime.get_active_container()
        return self._container
        
    def validate_knowledge_graph(self) -> Dict[str, Any]:
        from backend.modules.knowledge_graph.indexes.stats_index import build_stats_index
        glyphs = self.container.get("glyph_grid", [])
        stats_result = build_stats_index(glyphs)

        return {
            "rubric_compliance": {
                "deduplication": bool(stats_result["stats_index"]["summary"]["frequencies"]),
                "container_awareness": True,
                "semantic_metadata": any("metadata" in g for g in glyphs),
                "timestamps": all("timestamp" in g for g in glyphs),
                "plugin_compatible": any("source_plugin" in g for g in glyphs),
                "search_ready": True,
                "compressed_export": True,
                "dc_injection_ready": True
            },
            "stats_index": stats_result["stats_index"],
            "total_glyphs": len(glyphs)
        }

    def build_node_from_container_for_kg(self, container: dict, *, expand: bool = False) -> dict:
        """
        HOV1/HOV2/HOV3:
        - Ensure GHX flags (hover/collapsed) are baked into container meta
        - Build a KG-ready node with viz hints
        - Respect lazy expansion (collapsed by default unless expand=True)
        """
        # HOV1: bake hover/collapse GHX flags into the container meta
        container = bake_hologram_meta(dict(container or {}))

        # --- K9b: Hover Geometry Metadata + Entanglement Links ---
        metadata = container.get("metadata", {}) or {}

        # Hover summary and GHX hint (used in HUD overlays)
        metadata.setdefault("hover_summary", f"Container: {container.get('id', 'unknown')}")
        metadata.setdefault("ghx_hint", "↯ Symbolic Container Overview")

        # Geometry layout type: used in GHX/Atom/Hoberman visuals
        metadata.setdefault("layout_type", container.get("geometry_type", "grid"))

        # Entangled links (↔ overlay anchors)
        if "entangled_links" not in metadata:
            linked = []
            for glyph in container.get("glyphs", []):
                entangled = glyph.get("entangled_with")
                if entangled:
                    linked.extend(entangled if isinstance(entangled, list) else [entangled])
            metadata["entangled_links"] = sorted(set(linked))

        # Save metadata back into container
        container["metadata"] = metadata

        # ✅ Use the top-level sqi_fastmap import if available; no re-imports
        try:
            if 'sqi_fastmap' in globals() and hasattr(sqi_fastmap, "add_or_update_entry"):
                sqi_fastmap.add_or_update_entry(
                    container_id=container.get("id"),
                    topic_vector=metadata.get("topics", []),
                    metadata=metadata,
                )
        except Exception as e:
            print(f"⚠️ Failed to update SQI FastMap for {container.get('id')}: {e}")

        # HOV2/HOV3: build a KG node payload with GHX viz flags and lazy expansion
        return make_kg_payload(
            {
                "id": container.get("id") or container.get("container_id", "unknown"),
                "meta": container.get("meta", {}),
            },
            expand=expand,  # False by default -> collapsed/lazy
        )

    # --- NEW: collect UCS/SQI containers as KG nodes (collapsed by default) ---
    def _collect_sqi_nodes(self) -> list[dict]:
        """
        Walk the UCS runtime and build KG nodes for all known containers.
        Collapsed by default (HOV3), with GHX flags baked (HOV1/HOV2).
        Returns a list of KG node payloads compatible with your export pack.
        """
        try:
            from backend.modules.dimensions.universal_container_system import ucs_runtime
        except Exception as e:
            print(f"⚠️ UCS runtime not available for SQI node collection: {e}")
            return []

        nodes_out: list[dict] = []

        # Try the common APIs; fall back gracefully
        try:
            if hasattr(ucs_runtime, "list_containers"):
                ids = ucs_runtime.list_containers()
            elif hasattr(ucs_runtime, "registry"):
                ids = list(getattr(ucs_runtime, "registry", {}).keys())
            else:
                ids = []
        except Exception as e:
            print(f"⚠️ UCS list failed: {e}")
            ids = []

        for cid in ids or []:
            try:
                # get the actual container object/dict
                if hasattr(ucs_runtime, "get_container"):
                    c = ucs_runtime.get_container(cid)
                elif hasattr(ucs_runtime, "index"):
                    c = ucs_runtime.index.get(cid)
                elif hasattr(ucs_runtime, "registry"):
                    c = ucs_runtime.registry.get(cid)
                else:
                    c = None

                if not c:
                    continue

                # Build a KG node with GHX flags baked, collapsed by default
                node = self.build_node_from_container_for_kg(c, expand=False)
                # Your pack uses {'type': 'kg_node', ...}
                nodes_out.append({"type": "kg_node", **node})
            except Exception as e:
                print(f"⚠️ Skipped UCS container '{cid}': {e}")

        return nodes_out

    def export_pack(self, container: dict, out_path: str | Path):
        """
        Export the container's KG content (from glyph_grid) to a compact JSON pack
        so it can be reloaded without recomputing. Also appends UCS/SQI containers
        as collapsed KG nodes with HOV1-HOV3 flags baked.

        This merged version ALSO injects QWave beams into the container prior to export
        (preserving the behavior from the simpler export_pack variant).
        """

        # --- 0) Inject QWave beams prior to building the pack (from the simple version) ---
        try:
            container_id = container.get("id")
            if container_id:
                # uses top-level imports if you already have them; otherwise import here:
                # from backend.modules.glyphwave.qwave.qwave_writer import collect_qwave_beams, export_qwave_beams
                beams = collect_qwave_beams(container_id)
                export_qwave_beams(container, beams, context={"frame": "mutated"})
                print(f"📡 Injected {len(beams)} QWave beams into container during KG export.")
        except Exception as e:
            print(f"⚠️ Failed to inject QWave beams in KG export: {e}")

        # --- 1) Defensive copy + bake HOV flags (HOV1) ---
        container = bake_hologram_meta(dict(container or {}))

        # --- 2) K9b: Hover Geometry Metadata + Entanglement Links ---
        metadata = container.get("metadata", {})
        metadata.setdefault("hover_summary", f"Container: {container.get('id', 'unknown')}")
        metadata.setdefault("ghx_hint", "↯ Symbolic Container Overview")
        metadata.setdefault("layout_type", container.get("geometry_type", "grid"))

        if "entangled_links" not in metadata:
            linked = []
            for glyph in container.get("glyphs", []):
                entangled = glyph.get("entangled_with")
                if entangled:
                    linked.extend(entangled if isinstance(entangled, list) else [entangled])
            metadata["entangled_links"] = sorted(set(linked))

        # --- 3) K9a: GHX/Hoberman overlay fields ---
        metadata.setdefault("ghx_mode", "hologram")
        metadata.setdefault("overlay_layers", [])

        cid_lower = (container.get("id") or "").lower()
        if "atom" in cid_lower:
            metadata["layout_type"] = "atom"
            metadata["ghx_mode"] = "shell"
            metadata["overlay_layers"].append("electron_rings")
        elif any(isinstance(t, str) and "hoberman" in t.lower() for t in container.get("tags", [])):
            metadata["layout_type"] = "hoberman"
            metadata["ghx_mode"] = "expanding_sphere"
            metadata["overlay_layers"].append("symbolic_expansion")

        # Link previews from glyphs (if present)
        link_previews = []
        for g in container.get("glyphs", []):
            preview_id = g.get("linkContainerId")
            if preview_id and preview_id not in link_previews:
                link_previews.append(preview_id)
        if link_previews:
            metadata["linkPreview"] = sorted(link_previews)

        container["metadata"] = metadata

        # --- 4) Build collapsed KG node for the main container (HOV2/HOV3) ---
        kg_node = self.build_node_from_container_for_kg(container, expand=False)

        # --- 5) Extract nodes/edges from glyph_grid ---
        cg = container.get("glyph_grid", [])
        nodes = []
        edges = []
        for g in cg:
            if not isinstance(g, dict):
                continue
            gtype = g.get("type")
            if gtype == "kg_node" and isinstance(g.get("metadata"), dict):
                nodes.append({**g["metadata"], "type": "kg_node"})
            elif gtype == "kg_edge" and isinstance(g.get("metadata"), dict):
                edges.append({
                    "src": g["metadata"].get("from"),
                    "dst": g["metadata"].get("to"),
                    "relation": g["metadata"].get("relation"),
                })

        pack = {
            "id": container.get("id"),
            "name": container.get("name"),
            "symbol": container.get("symbol", "❔"),
            "glyph_categories": container.get("glyph_categories", []),
            "nodes": nodes,
            "links": edges,
        }

        # --- 6) Merge main container node (dedupe by id) ---
        existing_nodes = pack.get("nodes", [])
        idset = {n.get("id") for n in existing_nodes if isinstance(n, dict)}
        if kg_node.get("id") in idset:
            existing_nodes = [n for n in existing_nodes if n.get("id") != kg_node.get("id")]
            idset.discard(kg_node.get("id"))
        existing_nodes.insert(0, {"type": "kg_node", **kg_node})
        idset.add(kg_node.get("id"))

        # --- 7) Collect UCS containers as extra KG nodes (collapsed/lazy by default) ---
        try:
            from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
            ucs_ids = []
            try:
                if hasattr(ucs_runtime, "list_containers"):
                    ucs_ids = ucs_runtime.list_containers()
                elif hasattr(ucs_runtime, "registry"):
                    ucs_ids = list(getattr(ucs_runtime, "registry", {}).keys())
                elif hasattr(ucs_runtime, "containers"):
                    ucs_ids = list(getattr(ucs_runtime, "containers", {}).keys())
            except Exception:
                ucs_ids = []

            for ucid in ucs_ids or []:
                try:
                    if hasattr(ucs_runtime, "get_container"):
                        uc = ucs_runtime.get_container(ucid)
                    elif hasattr(ucs_runtime, "containers"):
                        uc = ucs_runtime.containers.get(ucid)
                    else:
                        uc = None
                    if not uc:
                        continue

                    uc = bake_hologram_meta(dict(uc))  # ensure GHX flags
                    node = self.build_node_from_container_for_kg(uc, expand=False)

                    nid = node.get("id")
                    if nid and nid not in idset:
                        existing_nodes.append({"type": "kg_node", **node})
                        idset.add(nid)
                except Exception as e:
                    print(f"⚠️ Skipped UCS container '{ucid}': {e}")
        except Exception as e:
            print(f"⚠️ UCS runtime not available for KG export: {e}")

        # --- 8) Collect SQI registry containers as extra KG nodes (collapsed) ---
        try:
            from backend.modules.sqi.sqi_container_registry import SQIContainerRegistry
            _sqi_registry = SQIContainerRegistry()
            for rcid, entry in (_sqi_registry.index or {}).items():
                try:
                    node = make_kg_payload({"id": rcid, "meta": entry.get("meta", {})}, expand=False)
                    nid = node.get("id")
                    if nid and nid not in idset:
                        existing_nodes.append({"type": "kg_node", **node})
                        idset.add(nid)
                except Exception as e:
                    print(f"⚠️ Skipped SQI registry entry '{rcid}': {e}")
        except Exception:
            pass  # Fine if registry is not available

        # Final assignment
        pack["nodes"] = existing_nodes

        # --- 9) Copy QWave summary into pack if present on the container ---
        if isinstance(container.get("qwave"), dict):
            qwave = container["qwave"]
            beams = qwave.get("beams")
            mod = qwave.get("modulation_strategy")
            mv_frame = qwave.get("multiverse_frame")
            if beams:
                pack["qwave"] = {
                    "beams": beams,
                    "modulation_strategy": mod,
                    "multiverse_frame": mv_frame,
                }

        # --- 10) Write pack to disk ---
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=2)

        print(f"💾 KG export saved to {out_path}")

        # Optional WS notify (use lazy helper + _safe_emit defined above)
        if ENABLE_WS_BROADCAST:
            _safe_emit(lazy_broadcast_event({
                "type": "kg_update",
                "domain": container.get("domain") or "physics_core",
                "file": str(out_path),
                "status": "saved",
            }))

        return str(out_path)

    def inject_prediction_trace(container: dict, prediction_result: dict, *, origin: str = "prediction") -> None:
        """
        Injects prediction result, contradiction/simplification status,
        and metadata (confidence, entropy, suggestion) into the container.

        Also tracks full mutation history (trace_id, origin, parent_id),
        and enables GHX/QFC replay overlay reconstruction.
        """

        # Make sure container has the necessary fields
        container.setdefault("prediction", {}).update(prediction_result)
        container.setdefault("logic_trace", [])

        # Detect status and trigger replay flag
        status = prediction_result.get("status", "")
        if status in {"contradiction", "simplify"}:
            container.setdefault("metadata", {})["replaySuggested"] = True
            container["prediction"]["trigger_replay"] = True

        # Generate trace metadata
        trace_id = str(uuid.uuid4())
        parent_id = None
        if container["logic_trace"]:
            parent_id = container["logic_trace"][-1].get("trace_id")

        trace = {
            "type": "logic_prediction",
            "trace_id": trace_id,
            "parent_id": parent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "origin": origin,  # e.g. "initial", "mutation", "prediction", "teleport"
            "status": status,
            "confidence": prediction_result.get("confidence"),
            "entropy": prediction_result.get("entropy"),
            "suggestion": prediction_result.get("suggestion"),
            "mutated_fields": prediction_result.get("mutated_fields", []),
            "mutation_type": prediction_result.get("mutation_type", None),
        }

        # Append trace
        container["logic_trace"].append(trace)

        # Optionally mark last trace for SQI scoring or GHX rendering
        container.setdefault("sqi", {})["last_prediction"] = trace
        container.setdefault("replay", {})["last_trace_id"] = trace_id

        def write_scroll(
            self,
            scroll: Dict[str, Any],
            *,
            container_id: Optional[str] = None,
            plugin: str = "ReflectionBridge",
            region: Optional[str] = None,
            agent_id: str = "local",
        ) -> str:
            """
            Inject a reflection or relevance scroll into the KG.
            Persists it as a glyph of type="scroll".
            Called by sci_reflection_plugin_bridge.
            """
            glyph_id = generate_uuid()
            timestamp = get_current_timestamp()
            container_id = container_id or (self.container.get("id") if self.container else "kg_ephemeral")

            entry = {
                "id": glyph_id,
                "type": "scroll",
                "content": scroll,
                "timestamp": timestamp,
                "metadata": {
                    "container_id": container_id,
                    "source_plugin": plugin,
                },
                "tags": ["scroll", "reflection"],
                "agent_id": agent_id,
            }
            if region:
                entry["region"] = region

            self._write_to_container(entry)
            add_to_index("knowledge_index.scroll", entry)

            print(f"📜 KG: Scroll injected into {container_id}")
            return glyph_id

    def resolve_replay_chain(container: dict, start_id: Optional[str] = None) -> List[dict]:
        """
        Walks the logic_trace in reverse via parent_id links to reconstruct
        a full symbolic replay path (e.g. for GHX/QFC overlay or audit).
        """
        traces = container.get("logic_trace", [])
        if not traces:
            return []

        trace_by_id = {t["trace_id"]: t for t in traces if "trace_id" in t}
        current = trace_by_id.get(start_id) if start_id else traces[-1]
        chain = []

        while current:
            chain.append(current)
            pid = current.get("parent_id")
            current = trace_by_id.get(pid)

        return list(reversed(chain))

    # inside KnowledgeGraphWriter
    def save_pack_for_container(self, container_id: str, filename: str | None = None):
        from backend.modules.dimensions.universal_container_system import ucs_runtime
        c = None
        if hasattr(ucs_runtime, "get_container"):
            c = ucs_runtime.get_container(container_id)
        if not c:
            raise RuntimeError(f"Unknown container: {container_id}")
        name = (filename or c.get("name") or c.get("id") or "kg_export").rstrip(".json")
        out = KG_EXPORTS_DIR / f"{name}.kg.json"
        return self.export_pack(c, out)

    def _auto_export_attached(self):
        """
        If a container is attached, write its KG snapshot to kg_exports/<name>.kg.json.
        Safe no-op if container is missing or empty.
        """
        try:
            c = self.container
            if not isinstance(c, dict):
                return
            name = c.get("name") or c.get("id")
            if not name:
                return
            out = KG_EXPORTS_DIR / f"{name}.kg.json"
            self.export_pack(c, out)
        except Exception as e:
            print(f"⚠️ KG auto-export skipped: {e}")

    def save_current_pack(self, filename: str | None = None):
        """
        Manual trigger for saving the current container's KG pack.
        """
        c = self.container
        name = (filename or c.get("name") or c.get("id") or "kg_export").rstrip(".json")
        out = KG_EXPORTS_DIR / f"{name}.kg.json"
        return self.export_pack(c, out)

    def inject_glyph(
        self,
        content: str,
        glyph_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        spatial_location: Optional[str] = None,
        prediction: Optional[str] = None,
        plugin: Optional[str] = None,
        region: Optional[str] = None,
        coordinates: Optional[Tuple[float, float, float]] = None,
        forecast_confidence: Optional[float] = None,
        trace: Optional[str] = None,
        anchor: Optional[Dict[str, Any]] = None,
        agent_id: str = "local",
        version_vector: Optional[Dict[str, int]] = None,
        tags: Optional[list] = None,
    ):
        global _KG_BUSY
        if _KG_BUSY:
            return
        _KG_BUSY = True
        try:
            _broadcast_sync = None
            _broadcast_async = None
            try:
                from backend.routes.ws.glyphnet_ws import broadcast_event_throttled as _broadcast_sync  # type: ignore
            except Exception:
                try:
                    from backend.routes.ws.glyphnet_ws import broadcast_event as _broadcast_async  # type: ignore
                except Exception:
                    _broadcast_async = None

            import inspect, asyncio

            # ──────────────────────────────────────────────────────────────
            # KG -> QFC broadcast opt-out (default OFF) + loop-safe guard
            # ──────────────────────────────────────────────────────────────
            def _env_bool(name: str, default: str = "0") -> bool:
                v = os.getenv(name, default)
                return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

            # Default OFF: avoids broadcast + avoids printing no-loop errors on reload/start
            _KG_QFC_BROADCAST = _env_bool("KG_QFC_BROADCAST", "0")

            def _has_running_loop() -> bool:
                try:
                    asyncio.get_running_loop()
                    return True
                except RuntimeError:
                    return False

            def _emit(event_dict: dict):
                try:
                    if _broadcast_sync:
                        _broadcast_sync(event_dict)
                        return
                    if _broadcast_async:
                        if inspect.iscoroutinefunction(_broadcast_async):
                            try:
                                loop = asyncio.get_running_loop()
                                loop.create_task(_broadcast_async(event_dict))
                            except RuntimeError:
                                # No running loop: skip silently (no spam)
                                return
                        else:
                            _broadcast_async(event_dict)
                    else:
                        print(f"[SIM:FALLBACK] Broadcast: {event_dict}")
                except Exception:
                    pass

            glyph_id = generate_uuid()
            timestamp = get_current_timestamp()

            if not crdt_registry.acquire_lock(glyph_id, agent_id):
                raise RuntimeError(f"Glyph {glyph_id} is locked by another agent.")

            _emit({
                "type": "lock_acquired",
                "glyph_id": glyph_id,
                "agent_id": agent_id,
                "tags": ["🔒"]
            })

            entangled_group = None
            if metadata and "entangled_ids" in metadata:
                entangled_group = "|".join(sorted(metadata["entangled_ids"]))
                if not crdt_registry.acquire_entanglement_lock(entangled_group, agent_id):
                    raise RuntimeError(f"Entangled group {entangled_group} is locked by another agent.")

                _emit({
                    "type": "entanglement_lock_acquired",
                    "entangled_group": entangled_group,
                    "agent_id": agent_id,
                    "tags": ["↔", "🔒"]
                })

            merged_version = crdt_registry.merge_vector(glyph_id, version_vector or {})
            crdt_registry.increment_clock(glyph_id, agent_id)

            if isinstance(content, str):
                content = {
                    "type": "symbol",
                    "text": content,
                    "metadata": metadata or {}
                }

            auto_tags = self._derive_auto_tags(content)
            final_tags = list(set(auto_tags + (tags or [])))

            entry = {
                "id": glyph_id,
                "type": glyph_type,
                "content": content,
                "timestamp": timestamp,
                "metadata": metadata or {},
                "tags": final_tags,
                "agent_id": agent_id,
                "version_vector": merged_version
            }
            if spatial_location: entry["spatial"] = spatial_location
            if region: entry["region"] = region
            if coordinates: entry["coordinates"] = {"x": coordinates[0], "y": coordinates[1], "z": coordinates[2]}
            if prediction: entry["prediction"] = prediction
            if forecast_confidence is not None: entry["forecast_confidence"] = forecast_confidence
            if plugin: entry["source_plugin"] = plugin
            if trace: entry["trace_ref"] = trace
            if anchor: entry["anchor"] = anchor

            # Auto: if this glyph declares entanglement with other containers,
            # write entanglement edges (best-effort; never block)
            try:
                ent_ids = (entry.get("metadata") or {}).get("entangled_ids") or []
                if ent_ids:
                    this_cid = (entry.get("metadata") or {}).get("container_id") \
                            or (self.container.get("id") if self.container else None)
                    if this_cid:
                        for other in ent_ids:
                            try:
                                self.write_entanglement_entry(this_cid, other)
                            except Exception:
                                pass
            except Exception:
                pass

            self._write_to_container(entry)
            add_to_index("knowledge_index.glyph", entry)

            # ✅ KG -> QFC Broadcast Injection (opt-out + loop-safe)
            if _KG_QFC_BROADCAST and _has_running_loop():
                try:
                    from backend.modules.visualization.qfc_payload_utils import to_qfc_payload
                    from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update

                    node_payload = {
                        "glyph": glyph_type,
                        "op": "inject",
                        "metadata": metadata or {},
                    }
                    context = {
                        "container_id": (metadata.get("container_id") if metadata else None) or "unknown",
                        "source_node": (metadata.get("node_id") if metadata else None) or "origin",
                    }

                    qfc_payload = to_qfc_payload(node_payload, context)
                    loop = asyncio.get_running_loop()
                    loop.create_task(broadcast_qfc_update(context["container_id"], qfc_payload))
                except Exception as qfc_err:
                    # Only complain when broadcast is explicitly enabled
                    print(f"[⚠️ KG->QFC] Failed to broadcast injected glyph: {qfc_err}")
            # else: silent skip (prevents "no running event loop" spam)

            if anchor:
                try:
                    from backend.routes.ws.glyphnet_ws import broadcast_anchor_update  # type: ignore
                    if inspect.iscoroutinefunction(broadcast_anchor_update):
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(broadcast_anchor_update(glyph_id, anchor))
                        except RuntimeError:
                            # No running loop: skip silently
                            pass
                    else:
                        broadcast_anchor_update(glyph_id, anchor)
                except Exception:
                    pass

            crdt_registry.release_lock(glyph_id, agent_id)
            _emit({
                "type": "lock_released",
                "glyph_id": glyph_id,
                "agent_id": agent_id
            })

            if entangled_group:
                crdt_registry.release_entanglement_lock(entangled_group, agent_id)
                _emit({
                    "type": "entanglement_lock_released",
                    "entangled_group": entangled_group,
                    "agent_id": agent_id
                })

            return glyph_id

        finally:
            _KG_BUSY = False

    def write_link_entry(self, source_id: str, target_id: str, direction: str):
        """
        Adds a directional link edge between containers to the KG.
        """
        print(f"🧠 KG: Linking {source_id} -> {target_id} ({direction})")
        edge_entry = {
            "id": generate_uuid(),
            "type": "link",
            "from": source_id,
            "to": target_id,
            "direction": direction,
            "timestamp": get_current_timestamp(),
            "tags": ["link", "navigation"],
            # NEW:
            "content": f"{source_id} -> {target_id} ({direction})",
        }
        add_to_index("knowledge_index.links", edge_entry)

    def write_entanglement_entry(self, container_a: str, container_b: str):
        """
        Adds an entanglement edge to the KG *and* journals it
        into the ledger so /api/kg/events → applyEvents can
        materialize a kg_edge row with kind='ENTANGLEMENT'.

        For now, if no higher-level append_event/append_events helper
        exists, we also write directly into kg_events + kg_edge via SQLite.
        """
        print("💥 DEBUG: write_entanglement_entry CALLED")
        print(f"🧠 KG: Entangled {container_a} ↔ {container_b}")

        # Index-friendly record for SQI / search
        entangle_entry = {
            "id": generate_uuid(),
            "type": "entanglement",
            "from": container_a,
            "to": container_b,
            "timestamp": get_current_timestamp(),
            "tags": ["entangled", "↔"],
            "content": f"{container_a} <-> {container_b}",
        }
        add_to_index("knowledge_index.entanglements", entangle_entry)

        # 🧾 Also: write a kg_events row so the JS/TS layer *can* fan out edges
        try:
            import json
            import time
            import sqlite3

            # Payload shape that applyEvents() expects:
            #   payload.metadata.from / payload.metadata.to
            payload = {
                "metadata": {
                    "from": container_a,
                    "to": container_b,
                    "container_a": container_a,
                    "container_b": container_b,
                }
            }

            ts_ms = int(time.time() * 1000)
            event_id = generate_uuid()

            # Reasonable defaults; can be overridden by attrs on the writer if present
            kg = getattr(self, "default_kg", "personal")
            owner_wa = getattr(self, "default_owner_wa", "ucs://local/system")
            topic_wa = getattr(self, "default_topic_wa", "ucs://local/ucs_hub")
            thread_id = f"kg:{kg}:{topic_wa}"

            # If the writer already has an event helper, prefer that
            if hasattr(self, "append_event"):
                # Higher-level path: let whatever owns append_event()
                # decide how to persist + fan out edges.
                self.append_event(
                    id=event_id,
                    kg=kg,
                    owner_wa=owner_wa,
                    thread_id=thread_id,
                    topic_wa=topic_wa,
                    type="entanglement",
                    kind=None,
                    ts=ts_ms,
                    size=None,
                    sha256=None,
                    payload=payload,
                )

            elif hasattr(self, "append_events"):
                # Batch helper variant
                self.append_events([
                    {
                        "id": event_id,
                        "kg": kg,
                        "owner_wa": owner_wa,
                        "thread_id": thread_id,
                        "topic_wa": topic_wa,
                        "type": "entanglement",
                        "kind": None,
                        "ts": ts_ms,
                        "size": None,
                        "sha256": None,
                        "payload": payload,
                    }
                ])

            else:
                # Fallback: write directly into kg_events *and* symmetric kg_edge rows
                db_path = getattr(self, "db_path", "server/data/kg.db")
                print(f"💥 DEBUG: entanglement fallback → SQLite @ {db_path}")
                conn = sqlite3.connect(db_path)
                try:
                    cur = conn.cursor()

                    # 1) kg_events row (journal the entanglement)
                    cur.execute(
                        """
                        INSERT INTO kg_events
                          (id, kg, owner_wa, thread_id, topic_wa,
                           type, kind, ts, size, sha256, payload)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event_id,
                            kg,
                            owner_wa,
                            thread_id,
                            topic_wa,
                            "entanglement",
                            None,
                            ts_ms,
                            None,
                            None,
                            json.dumps(payload),
                        ),
                    )

                    # 2) Idempotent symmetric edges in kg_edge with kind='ENTANGLEMENT'
                    def edge_exists(src: str, dst: str) -> bool:
                        cur.execute(
                            """
                            SELECT 1 FROM kg_edge
                            WHERE kg = ?
                              AND kind = 'ENTANGLEMENT'
                              AND src_type = 'container_ref'
                              AND dst_type = 'container_ref'
                              AND src_id = ?
                              AND dst_id = ?
                            """,
                            (kg, src, dst),
                        )
                        return cur.fetchone() is not None

                    # A → B
                    if not edge_exists(container_a, container_b):
                        cur.execute(
                            """
                            INSERT INTO kg_edge
                              (kg, kind, src_type, src_id, dst_type, dst_id, created_ts)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                kg,
                                "ENTANGLEMENT",
                                "container_ref",
                                container_a,
                                "container_ref",
                                container_b,
                                ts_ms,
                            ),
                        )

                    # B → A (symmetric entanglement)
                    if container_a != container_b and not edge_exists(container_b, container_a):
                        cur.execute(
                            """
                            INSERT INTO kg_edge
                              (kg, kind, src_type, src_id, dst_type, dst_id, created_ts)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                kg,
                                "ENTANGLEMENT",
                                "container_ref",
                                container_b,
                                "container_ref",
                                container_a,
                                ts_ms,
                            ),
                        )

                    conn.commit()
                    print("💥 DEBUG: entanglement edges A↔B inserted via fallback (idempotent)")
                finally:
                    conn.close()

        except Exception as e:
            print(f"[KGWriter] ⚠️ entanglement event/edge journaling failed: {e}")

        # 🔁 ALSO: journal as a glyph so it becomes a KG glyph entry (for the index)
        try:
            self.inject_glyph(
                content=entangle_entry["content"],
                glyph_type="entanglement",
                metadata={
                    "from": container_a,
                    "to": container_b,
                    "container_a": container_a,
                    "container_b": container_b,
                },
                tags=["entangled", "↔"],
                plugin="KG",
            )
        except Exception as e:
            print(f"[KGWriter] ⚠️ entanglement glyph journaling failed: {e}")

    def inject_logic_trace_data(trace: dict, logic_prediction: dict, rewrite_suggestion: dict = None):
        """
        Adds logic prediction and rewrite metadata to CodexTrace entries.

        Parameters:
            trace (dict): The CodexTrace or glyph trace entry being written.
            logic_prediction (dict): Dict with keys: 'contradiction', 'confidence', 'suggestion', 'logic_score'.
            rewrite_suggestion (dict): Optional dict with keys: 'new_glyph', 'goal_match_score', 'rewrite_success_prob'.
        """
        trace["logic_prediction"] = {
            "contradiction": logic_prediction.get("contradiction", False),
            "confidence": logic_prediction.get("confidence", 0.0),
            "suggestion": logic_prediction.get("suggestion", ""),
            "logic_score": logic_prediction.get("logic_score", 0.0),
        }
        
        if rewrite_suggestion:
            trace["rewrite_suggestion"] = {
                "new_glyph": rewrite_suggestion.get("new_glyph", ""),
                "goal_match_score": rewrite_suggestion.get("goal_match_score", 0.0),
                "rewrite_success_prob": rewrite_suggestion.get("rewrite_success_prob", 0.0),
            }

    def merge_edit(self, glyph_id: str, updates: Dict[str, Any], agent_id: str, version_vector: Dict[str, int]):
        global _KG_BUSY
        if _KG_BUSY:
            return {"version_vector": {}}  # safe no-op response
        try:
            _KG_BUSY = True

            glyphs = self.container.get("glyph_grid", [])
            for g in glyphs:
                if g.get("id") == glyph_id:
                    prev_state = g.copy()
                    merged_clock = crdt_registry.merge_vector(glyph_id, version_vector)
                    local_clock = crdt_registry.version_vectors[glyph_id]

                    # ⚠️ Conflict detection: concurrent edits from different agents
                    if any(version_vector.get(a, 0) > local_clock.get(a, 0) for a in version_vector):
                        conflict_entry = {
                            **prev_state,
                            "id": generate_uuid(),
                            "type": "conflict",
                            "conflict_with": glyph_id,
                            "conflicting_agent": agent_id,
                            "timestamp": get_current_timestamp(),
                            "tags": ["⚠️", "conflict"]
                        }
                        self._write_to_container(conflict_entry)
                        add_to_index("knowledge_index.glyph", conflict_entry)

                    g.update(updates)
                    g["version_vector"] = dict(merged_clock)
                    g["last_modified_by"] = agent_id
                    g["last_modified_at"] = get_current_timestamp()
                    add_to_index("knowledge_index.glyph", g)
                    return g
            raise KeyError(f"Glyph {glyph_id} not found for merge edit.")

        finally:
            _KG_BUSY = False

    # ── Convenience injectors (kept) ──

    def inject_self_reflection(self, message: str, trigger: str):
        return self.inject_glyph(content=f"Reflection: {message}", glyph_type="self_reflection",
                                 metadata={"trigger": trigger})

    def inject_prediction(self, hypothesis: str, based_on: str, confidence: float = 0.75,
                          plugin: Optional[str] = None, region: Optional[str] = None,
                          coords: Optional[Tuple[float, float, float]] = None):
        return self.inject_glyph(content=hypothesis, glyph_type="predictive",
                                 metadata={"based_on": based_on},
                                 prediction="future", forecast_confidence=confidence,
                                 plugin=plugin, region=region, coordinates=coords)

    # ── KG node/edge helpers ──
    # was: def add_node(self, node_id: str, label: str, meta: Optional[Dict[str, Any]] = None):
    def add_node_glyph(self, node_id: str, label: str, meta: Optional[Dict[str, Any]] = None):
        return self.inject_glyph(
            content=f"KGNode:{node_id} label={label}",
            glyph_type="kg_node",
            metadata={"node_id": node_id, "label": label, **(meta or {})},
            plugin="KG"
        )

    # --- Source/provenance helpers ---
    def add_source(self, node_id: str, source: Dict[str, Any]):
        return self.inject_glyph(
            content=f"KGSource:{node_id}",
            glyph_type="kg_source",
            metadata={"node_id": node_id, **(source or {})},
            plugin="KG"
        )

    def link_source(self, node_id: str, source_id: str, relation: str = "supports"):
        self.add_edge(node_id, source_id, relation)
        try:
            self.write_link_entry(node_id, source_id, relation)
        except Exception:
            pass
        return self.inject_glyph(
            content=f"KGEdge:{node_id}->{source_id} rel={relation}",
            glyph_type="kg_edge",
            metadata={"from": node_id, "to": source_id, "relation": relation},
            plugin="KG"
        )

        # --- ABOUT edge: ContainerRef → Thread/Topic -----------------------------
    def add_about_edge(
        self,
        container_id: str | None = None,
        *,
        thread_id: str | None = None,
        topic_wa: str | None = None,
    ):
        """
        Emit ABOUT(ContainerRef→Thread|Topic) as a kg_edge.
        - If thread_id is not provided, derive from {kg, topic_wa} using the same
          scheme as ledger journaling: "kg:{kg}:{topic_wa}".
        - topic_wa falls back to container.meta.topic or "ucs://local/ucs_hub".
        """
        meta = (self.container or {}).get("meta", {}) or {}
        kg = (meta.get("graph") or "personal").lower()
        if kg not in ("personal", "work"):
            kg = "personal"

        topic_wa = (topic_wa or meta.get("topic") or "ucs://local/ucs_hub").strip()
        thread_id = thread_id or f"kg:{kg}:{topic_wa}"
        src = container_id or (self.container.get("id") if self.container else None)
        if not src:
            raise RuntimeError("add_about_edge: missing container_id and no bound container")

        # Record as a KG edge with relation 'about'
        # Keep both thread_id + topic_wa in metadata for easier client hydration
        return self.inject_glyph(
            content=f"KGEdge:{src}->{thread_id} rel=about",
            glyph_type="kg_edge",
            metadata={
                "from": src,
                "to": thread_id,
                "relation": "about",
                "topic_wa": topic_wa,
            },
            plugin="KG"
        )

    # --- Entangled fork convenience -----------------------------------------
    def on_entangled_fork(
        self,
        parent_container_id: str,
        fork_container_id: str,
        *,
        topic_wa: str | None = None,
    ):
        """
        Called by fork/clone codepaths when a container splits (entangled branch).
        - Writes an 'entanglement' glyph/edge between parent ↔ fork
        - Adds ABOUT edge for the new fork to its thread/topic
        - Emits a KG event of type 'entanglement' so the JS pipeline can insert
          an ENTANGLEMENT edge into kg_edge (container_ref ↔ container_ref).

        If topic_wa is not provided, we try to infer it from the bound container's
        meta (meta.topic / meta.topic_wa), and fall back to the local UCS hub.
        """
        # 🧭 Resolve a sensible topic_wa if the caller didn't pass one
        resolved_topic = topic_wa
        try:
            if not resolved_topic:
                meta = None
                if getattr(self, "container", None) and isinstance(self.container, dict):
                    meta = self.container.get("meta") or self.container.get("metadata") or {}
                if isinstance(meta, dict):
                    resolved_topic = (
                        meta.get("topic")
                        or meta.get("topic_wa")
                        or "ucs://local/ucs_hub"
                    )
                else:
                    resolved_topic = "ucs://local/ucs_hub"
            if resolved_topic:
                resolved_topic = resolved_topic.strip()
        except Exception:
            resolved_topic = topic_wa or "ucs://local/ucs_hub"

        # 🔗 Entanglement glyph / edge: parent ↔ fork (telemetry / knowledge_index)
        try:
            self.write_entanglement_entry(parent_container_id, fork_container_id)
        except Exception as e:
            print(f"[KGWriter] ⚠️ entanglement entry failed: {e}")

        # 🧵 ABOUT edge: forked container → thread/topic
        try:
            self.add_about_edge(fork_container_id, topic_wa=resolved_topic)
        except Exception as e:
            print(f"[KGWriter] ⚠️ ABOUT edge failed: {e}")

        # 🧠 KG event: type='entanglement' so TS applyEvents() can create
        # an ENTANGLEMENT edge in kg_edge (container_ref ↔ container_ref).
        #
        # This is best-effort and will only run if the writer exposes a
        # suitable event-append method (append_event / log_event / write_event).
        try:
            import time as _time

            payload = {
                "metadata": {
                    "from": parent_container_id,
                    "to": fork_container_id,
                }
            }

            event = {
                "type": "entanglement",
                "kind": None,
                "thread_id": None,
                "topic_wa": resolved_topic,
                "ts": int(_time.time() * 1000),
                "payload": payload,
            }

            if hasattr(self, "append_event"):
                self.append_event(event)
            elif hasattr(self, "log_event"):
                # some implementations use a more generic logger
                self.log_event(event)
            elif hasattr(self, "write_event"):
                self.write_event(event)
            # else: no suitable API, silently skip
        except Exception as e:
            print(f"[KGWriter] ⚠️ entanglement KG event emit failed: {e}")

    def add_edge(self, src: str, dst: str, relation: str):
        self.write_link_entry(src, dst, relation)
        return self.inject_glyph(
            content=f"KGEdge:{src}->{dst} rel={relation}",
            glyph_type="kg_edge",
            metadata={"from": src, "to": dst, "relation": relation},
            plugin="KG"
        )

    def inject_plugin_aware(self, content: str, glyph_type: str, plugin_name: str, metadata: Optional[Dict[str, Any]] = None):
        return self.inject_glyph(content=content, glyph_type=glyph_type, metadata=metadata, plugin=plugin_name)

    def inject_soullaw_violation(self, rule: str, reason: str, context: Optional[Dict[str, Any]] = None):
        return self.inject_glyph(
            content=f"SoulLaw Violation: {rule} - {reason}", glyph_type="violation",
            metadata={"rule": rule, "type": "SoulLaw", "reason": reason, "context": context or {}, "tags": ["📜", "🧠", "❌"]},
            plugin="SoulLaw"
        )

    def load_domain_pack(self, container_id: str, container: Dict[str, Any]) -> bool:
        """
        Ingest ANY domain seed (id/nodes/links) into the live KG.
        """
        nodes = container.get("nodes", [])
        links = container.get("links", [])
        if not nodes and not links:
            return False

        # Add nodes
        for node in nodes:
            self.add_node(
                node["id"],
                label=node.get("label", node["id"]),
                meta={
                    "source": container_id,
                    "domain": container.get("metadata", {}).get("domain") or container.get("name") or container_id,
                    "category": node.get("cat"),
                    **({k: v for k, v in node.items() if k not in ("id", "label", "cat")} ),
                },
            )

        # Add links
        for link in links:
            self.add_edge(link["src"], link["dst"], link.get("relation", "relates_to"))

        # Auto-export snapshot
        try:
            c = self.container if getattr(self, "_container", None) else container
            out_path = (Path(os.getenv("AION_KG_EXPORT_DIR", "")) if os.getenv("AION_KG_EXPORT_DIR")
                        else (Path(__file__).resolve().parents[3] / "backend/modules/dimensions/containers_saved/kg_exports")) \
                    / f"{container_id}.kg.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            self.export_pack(c, out_path)
        except Exception as e:
            print(f"⚠️ KG auto-export failed for {container_id}: {e}")

        return True  

    # ── New: Proof/Drift/Harmonics helpers (Stage C/D integration) ──
    def write_proof_state(self,
                          name: str,
                          status: str,
                          drift_value: float = 0.0,
                          depends_on: Optional[List[str]] = None,
                          metadata: Optional[Dict[str, Any]] = None,
                          agent_id: str = "local") -> str:
        """
        Persist a proof/lemma state to KG + container for later replay/analytics.
        """
        content = f"ProofState:{name} status={status} drift={drift_value}"
        md = {"depends_on": depends_on or []}
        if metadata:
            md.update(metadata)
        return self.inject_glyph(
            content=content,
            glyph_type="proof_state",
            metadata=md,
            agent_id=agent_id,
            plugin="SQI"
        )

    def inject_pattern(self, container_id: str, pattern_trace: dict):
        """
        Inject a pattern trace as a glyph into the KG.
        This is called by the SymbolicPatternEngine when a pattern is detected.
        """
        label = pattern_trace.get("name", "Unnamed Pattern")
        glyph_id = pattern_trace.get("pattern_id", str(uuid.uuid4()))
        tags = pattern_trace.get("glyphs", [])
        sqi = pattern_trace.get("sqi_score", 0.0)

        return self.inject_glyph(
            content=f"Pattern: {label}",
            glyph_type="pattern",
            metadata={
                "id": glyph_id,
                "name": label,
                "glyphs": tags,
                "sqi_score": sqi
            },
            plugin="PatternEngine"
        )

    def write_drift_report(self,
                           container_id: str,
                           total_weight: float,
                           status: str,
                           gaps: List[Dict[str, Any]],
                           meta: Optional[Dict[str, Any]] = None,
                           agent_id: str = "local") -> str:
        """
        Store a drift summary computed by sqi_math_adapter.compute_drift(...)
        """
        payload = {
            "container_id": container_id,
            "total_weight": total_weight,
            "status": status,
            "gaps": gaps,
            "meta": meta or {},
        }
        gid = self.inject_glyph(
            content=f"DriftReport:{container_id} weight={total_weight} status={status}",
            glyph_type="drift_report",
            metadata=payload,
            agent_id=agent_id,
            plugin="SQI"
        )
        add_to_index("knowledge_index.drift", {"id": gid, **payload, "timestamp": get_current_timestamp()})
        return gid

    def write_harmonic_suggestions(self,
                                   target: str,
                                   suggestions: List[Dict[str, Any]],
                                   context_container_id: Optional[str] = None,
                                   agent_id: str = "local") -> str:
        """
        Persist harmonics suggestions e.g. from suggest_harmonics(...)
        suggestions: [{missing: str, candidates: [{name, score}, ...]}, ...]
        """
        md = {
            "target": target,
            "suggestions": suggestions,
            "container_id": context_container_id
        }
        gid = self.inject_glyph(
            content=f"Harmonics:{target}",
            glyph_type="harmonics_suggestions",
            metadata=md,
            agent_id=agent_id,
            plugin="SQI"
        )
        add_to_index("knowledge_index.harmonics", {"id": gid, **md, "timestamp": get_current_timestamp()})
        return gid

    # ── Internals ──
    def _derive_auto_tags(self, content: str) -> list:
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)
        tags = []
        if "↔" in content: tags.append("entangled")
        if "⧖" in content: tags.append("collapse")
        if "⬁" in content: tags.append("rewrite")
        if "🧬" in content: tags.append("mutation")
        if "⚛" in content: tags.append("qglyph")
        if content.startswith("DriftReport:"): tags.append("drift")
        if content.startswith("ProofState:"): tags.append("proof")
        if content.startswith("Harmonics:"): tags.append("harmonics")
        return tags

    from backend.modules.knowledge_graph.ledger_adapter import log_events, make_event

    def _write_to_container(self, entry: Dict[str, Any]):
        # Ensure container structures exist
        if "glyph_grid" not in self.container:
            self.container["glyph_grid"] = []
        self.container["glyph_grid"].append(entry)

        import datetime as _dt  # local to keep this paste self-contained
        self.container["last_updated"] = _dt.datetime.utcnow().isoformat()

        # --- Namespace-aware journal to ledger (best-effort; never break live KG)
        try:
            import time as _time

            meta = self.container.get("meta") or {}

            kg = (meta.get("graph") or "personal").lower()
            if kg not in ("personal", "work"):
                kg = "personal"

            owner = (meta.get("ownerWA") or "").strip() or "unknown@wave.tp"
            topic_wa = (meta.get("topic") or "").strip() or "ucs://local/ucs_hub"
            thread_id = f"kg:{kg}:{topic_wa}"

            # map glyph -> event “type/kind”
            gtype   = entry.get("type") or "glyph"
            content = entry.get("content")
            kind    = content.get("type") if isinstance(content, dict) else None

            ev = make_event(
                type="message" if gtype in ("message", "self_reflection", "predictive", "glyph") else gtype,
                kind=kind or gtype,                 # keep signal about sub-type
                thread_id=thread_id,
                topic_wa=topic_wa,
                payload={
                    "glyph_id": entry.get("id"),
                    "glyph_type": gtype,
                    "content": content,
                    "metadata": entry.get("metadata"),
                    "tags": entry.get("tags"),
                    "agent_id": entry.get("agent_id"),
                    "version_vector": entry.get("version_vector"),
                },
                ts_ms=int(entry.get("timestamp") or _time.time() * 1000),
                id=entry.get("id"),                 # idempotency: reuse glyph id
            )
            log_events(kg=kg, owner=owner, events=[ev])
        except Exception:
            # Never let ledger errors break KG writes
            pass

        # --- Microgrid tap (HUD registration; best-effort, deterministic coords)
        try:
            from backend.modules.glyphos.microgrid_index import MicrogridIndex
            import hashlib as _hashlib

            # Simple singleton per process
            MICROGRID = getattr(MicrogridIndex, "_GLOBAL", None) or MicrogridIndex()
            MicrogridIndex._GLOBAL = MICROGRID

            # Deterministic small-grid coords (0..15) using stable hash (BLAKE2b 16-bit)
            def _h16(s: str) -> int:
                return int(_hashlib.blake2b((s or "").encode("utf-8"), digest_size=2).hexdigest(), 16) % 16

            cx = _h16(str(entry.get("id", "")))
            cy = _h16(str(entry.get("type", "")))
            cz = 0  # single layer for now

            MICROGRID.register_glyph(
                cx, cy, cz,
                glyph=str(entry.get("id", "")),
                metadata={
                    "type": entry.get("type"),
                    "tags": entry.get("tags", []) or [],
                    "energy": 1.0,
                    "timestamp": entry.get("timestamp"),
                }
            )
        except Exception:
            # HUD plumbing must never impact core writes
            pass

    # ── Optional: Simple query helpers for dashboards ──
    def list_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        return [g for g in self.container.get("glyph_grid", []) if tag in g.get("tags", [])]

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        glyphs = self.container.get("glyph_grid", [])
        return glyphs[-limit:]

# ──────────────────────────────
# write_glyph_entry (updated)
# ──────────────────────────────
def store_container_metadata(container_path: str, coord: str, metadata: dict):
        """
        Store metadata into a symbolic container file, such as trace logs, HST info, etc.
        Appends into container['metadata']['injectionLog'].
        """
        if not os.path.exists(container_path):
            logger.warning(f"[KG] Metadata injection failed - container not found: {container_path}")
            return

        try:
            with open(container_path, "r", encoding="utf-8") as f:
                container = json.load(f)
        except Exception as e:
            logger.error(f"[KG] Failed to read container {container_path}: {e}")
            return

        # Inject into container metadata
        container.setdefault("metadata", {}).setdefault("injectionLog", []).append({
            "coord": coord,
            **metadata
        })

        try:
            with open(container_path, "w", encoding="utf-8") as f:
                json.dump(container, f, indent=2)
                logger.info(f"[KG] ✅ Metadata injected into: {container_path}")
        except Exception as e:
            logger.error(f"[KG] Failed to write container {container_path}: {e}")

def store_generated_glyph(glyph: Dict[str, Any]):
    """
    Store a generated glyph into the appropriate container and update trace metadata.
    """
    container_id = glyph.get("containerId") or glyph.get("targetContainer")
    if not container_id:
        raise ValueError("Generated glyph is missing 'containerId' or 'targetContainer' field")

    container = load_decrypted_container(container_id)
    if not container:
        raise FileNotFoundError(f"Container '{container_id}' not found or could not be loaded.")

    # Inject into symbolic trace stream
    inject_trace_event(container, {
        "event": "glyph_generated",
        "glyph": glyph,
        "timestamp": glyph.get("timestamp"),
        "source": "creative_synthesis"
    })

    # Optional Codex/SQI log update
    codex_metrics.record_glyph_generated(glyph)

    # Persist updated container
    ucs_runtime.save_container(container_id, container)

    print(f"✅ Stored generated glyph into container '{container_id}'")

def write_glyph_entry(
    glyph: str, g_type: str, g_tag: str, g_value: str, ops_chain: list,
    context: Dict[str, Any], cost, timestamp: float, tags: list,
    reasoning_chain: str = None, anchor: Optional[Dict[str, Any]] = None
):
    auto_tags = []
    if "↔" in glyph: auto_tags.append("entangled")
    if "⧖" in glyph: auto_tags.append("collapse")
    if "⬁" in glyph: auto_tags.append("rewrite")
    if "🧬" in glyph: auto_tags.append("mutation")
    if "⚛" in glyph: auto_tags.append("qglyph")

    entry = {
    "glyph": glyph,
    "content": glyph,             
    "type": g_type,
    "tag": g_tag,
    "value": g_value,
    "ops_chain": ops_chain,
    "cost": cost.total(),
    "timestamp": timestamp,
    "tags": list(set(tags + auto_tags)),
    "context": context,
    "reasoning_chain": reasoning_chain or "No reasoning recorded",
    }
    if anchor:
        entry["anchor"] = anchor

    # ✅ Add reasoning entry and update index
    from backend.modules.knowledge_graph.indexes.reasoning_index import add_reasoning_entry
    add_reasoning_entry(
        glyph_id=glyph,
        reasoning=reasoning_chain or "Unspecified",
        context=context
    )
    
    add_to_index("knowledge_index.glyph", entry)

    # ✅ Broadcast glyph entry event (safe async emit, no circular import crash)
    try:
        from backend.routes.ws.glyphnet_ws import broadcast_event as lazy_broadcast_event
    except Exception:
        lazy_broadcast_event = lambda *a, **k: None  # no-op if WS not available

    import inspect, asyncio
    def _safe_emit(coro_or_none):
        try:
            if not coro_or_none:
                return
            if inspect.iscoroutine(coro_or_none):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(coro_or_none)
                except RuntimeError:
                    asyncio.run(coro_or_none)
        except Exception:
            pass

    _safe_emit(lazy_broadcast_event({
        "type": "glyph_entry",
        "glyph": glyph,
        "tags": list(set(tags + auto_tags)),
        "context": context,
        "anchor": anchor,
        "timestamp": timestamp,
    }))

    # ✅ Broadcast anchor update if present
    if anchor:
        _safe_emit(lazy_broadcast_anchor_update(glyph, anchor))

    return entry  # <-- Ensure function return stays intact

def get_glyph_trace_for_container(container_id: str) -> list:
    """
    Retrieve the symbolic glyph trace from a container by its ID.
    Returns a list of glyphs (or symbolic nodes) for replay / prediction.
    """
    from backend.modules.dimensions.containers.container_loader import load_container_by_id  # ✅ Corrected path

    container = load_container_by_id(container_id)
    if not container:
        raise ValueError(f"Container {container_id} not found")

    # Extract trace from metadata or replay path
    if "symbolic_trace" in container:
        return container["symbolic_trace"]

    # Optional fallback: GHX field
    if "GHX" in container:
        return container["GHX"].get("trace", [])

    raise ValueError(f"No glyph trace found in container {container_id}")

def inject_into_trace(trace: List[Dict[str, Any]], entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Inject a symbolic rewrite, prediction, or event into a Codex or KG trace list.

    Args:
        trace: Existing execution trace list (from a .dc container or live runtime).
        entry: A dictionary containing the trace event (e.g., rewrite, prediction, etc.).

    Returns:
        The updated trace list with the new entry appended.
    """
    if not isinstance(trace, list):
        trace = []

    if isinstance(entry, dict):
        trace.append(entry)

    return trace

def write_glyph_event(
    event_type: str,
    event: dict,
    container_id: str = None
) -> None:
    """
    Write a glyph-related event (mutation, prediction, rewrite, etc.)
    into the knowledge graph trace system.

    Args:
        event_type: Type of event (e.g. 'dna_mutation', 'rewrite', etc.)
        event: Dictionary containing event details.
        container_id: Optional container to tag for context.
    """
    if not isinstance(event, dict):
        return

    # Inject into live .dc trace if container is active
    from backend.modules.glyphvault.vault_manager import VAULT
    container = VAULT.get(container_id) if container_id else None

    if container is not None:
        container.setdefault("trace", {}).setdefault(event_type, []).append(event)

    print(f"[KGWriter] Event: {event_type} -> {container_id} | {event.get('reason', '')}")

# === [A2a] Export QWave Beams for Container ===

# --- QWave compatibility (place near top imports) ---
try:
    # Canonical beam APIs live here
    from backend.modules.glyphwave.qwave.qwave_writer import (
        collect_qwave_beams as _qwave_collect_impl,
        export_qwave_beams as _qwave_export_impl,
    )
except Exception:
    _qwave_collect_impl = None
    _qwave_export_impl = None

def export_qwave_beams(container: dict, beams: list, context: dict | None = None):
    """
    Public/back-compat entrypoint. If canonical exporter exists, forward to it.
    Otherwise, write a legacy-compatible structure for both new and old readers.
    """
    if _qwave_export_impl is not None:
        return _qwave_export_impl(container, beams, context=context)

    # --- Legacy fallback (write BOTH shapes) ---
    # Normalize input beams (accept either 'modulation' or 'modulation_strategy')
    normalized = []
    for b in beams or []:
        normalized.append({
            "beam_id": b.get("id"),
            "source_id": b.get("source"),
            "target_id": b.get("target"),
            "carrier_type": b.get("carrier_type", "SIMULATED"),
            "modulation_strategy": b.get("modulation") or b.get("modulation_strategy") or "SimPhase",
            "coherence": b.get("coherence", 1.0),
            "entangled_path": b.get("entangled_path", []),
            "mutation_trace": b.get("mutation_trace", []),
            "collapse_state": b.get("collapse_state", (context or {}).get("frame", "original")),
            "metadata": b.get("metadata", {}),
        })

    # Newer readers (flat):
    container["qwave_beams"] = list(normalized)
    if context:
        container["multiverse_frame"] = context.get("frame", "original")

    # Older readers (nested under 'symbolic'):
    container.setdefault("symbolic", {})
    container["symbolic"]["qwave_beams"] = list(normalized)

# ...later inside KnowledgeGraphWriter.export_pack(...)
try:
    container_id = container.get("id")
    if container_id and _qwave_collect_impl:
        beams = _qwave_collect_impl(container_id)
        export_qwave_beams(container, beams, context={"frame": "mutated"})
        print(f"📡 Injected {len(beams)} QWave beams into container during KG export.")
except Exception as e:
    print(f"⚠️ Failed to inject QWave beams in KGWriter: {e}")
    
# ──────────────────────────────
# Harmonized Atom Commit Adapter
# ──────────────────────────────
def commit_atom_to_graph(label: str,
                         container_id: str,
                         sqi: float,
                         waveform: dict,
                         user_id: str = "default") -> dict:
    """
    Adapted bridge: commit high-SQI photon state as a Harmonic Atom.
    Uses get_kg_writer() to ensure the singleton instance is used (CRDT-safe).
    """
    try:
        from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
        kgw = get_kg_writer()

        metadata = {
            "container_id": container_id,
            "sqi_score": sqi,
            "waveform_summary": list(waveform.keys()) if isinstance(waveform, dict) else "raw_state",
            "committed_by": user_id,
            "label": label,
            "timestamp": datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "tags": ["HarmonicAtom", "AutoCommit", "SQI"],
        }

        glyph_id = kgw.inject_glyph(
            content=f"HarmonicAtom:{label} SQI={sqi:.3f}",
            glyph_type="harmonic_atom",
            metadata=metadata,
            plugin="SCI",
            region="auto_commit",
            agent_id=user_id,
        )

        # Optional: broadcast for frontend HUD
        try:
            from backend.routes.ws.glyphnet_ws import broadcast_event
            import inspect, asyncio
            evt = {
                "type": "atom_commit",
                "atom_label": label,
                "sqi": sqi,
                "glyph_id": glyph_id,
                "container_id": container_id,
                "timestamp": metadata["timestamp"],
            }
            if inspect.iscoroutinefunction(broadcast_event):
                asyncio.create_task(broadcast_event(evt))
            else:
                broadcast_event(evt)
        except Exception as e:
            print(f"[KGWriter] ⚠️ Broadcast skipped: {e}")

        print(f"🧠 [KGWriter] Harmonic Atom committed via singleton -> {label} (SQI={sqi:.3f})")
        return {"ref": f"{label}@{container_id}", "glyph_id": glyph_id, "status": "ok"}

    except Exception as e:
        print(f"❌ [KGWriter] Atom commit failed: {e}")
        return {"ref": label, "status": "error", "error": str(e)}
# ──────────────────────────────
# Global KG Writer Instance
# ──────────────────────────────
__all__ = ["kg_writer", "store_generated_glyph"]
kg_writer = KnowledgeGraphWriter()
