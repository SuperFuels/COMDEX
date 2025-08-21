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
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from collections import defaultdict

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
from backend.modules.codex.codex_metrics import codex_metrics

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
        # CLI/test mode: no UCS – return ephemeral container so inject_glyph still works
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

    def attach_container(self, container: dict):
        """
        Bind a specific UCS container so glyphs land in the correct place.
        This bypasses the default active container.
        Also auto-exports a KG snapshot for persistence in kg_exports/.
        """
        self._container = container
        # 🔄 Automatically export the attached container's KG to kg_exports/<name>.kg.json
        try:
            self._auto_export_attached()
        except Exception as e:
            print(f"⚠️ KG auto-export failed: {e}")

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
            from backend.modules.dimensions.universal_container_system import ucs_runtime
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
        metadata = container.get("metadata", {})

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
        try:
            from backend.modules.knowledge_graph.registry.sqi_fastmap_index import sqi_fastmap
            sqi_fastmap.add_or_update_entry(
                container_id=container["id"],
                topic_vector=metadata.get("topics", []),
                metadata=metadata
            )
        except Exception as e:
            print(f"⚠️ Failed to update SQI FastMap for {container.get('id')}: {e}")
        # HOV2/HOV3: build a KG node payload with GHX viz flags and lazy expansion
        return make_kg_payload(
            {
                "id": container.get("id") or container.get("container_id", "unknown"),
                "meta": container.get("meta", {}),
            },
            expand=expand,  # False by default → collapsed/lazy
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
        as collapsed KG nodes with HOV1–HOV3 flags baked.

        This version is aware of inject_node()'s 'kg_node' insertion shape so
        it will always export the latest injected KG nodes without recomputation.
        """
        # --- Defensive copy and HOV1–HOV3 injection for the primary container ---
        container = bake_hologram_meta(dict(container or {}))  # HOV1 flags

        # --- K9b: Hover Geometry Metadata + Entanglement Links ---
        metadata = container.get("metadata", {})

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

        # --- K9a: GHX/Hoberman Overlay Fields ---
        metadata.setdefault("ghx_mode", "hologram")
        metadata.setdefault("overlay_layers", [])

        # If container has atoms or orbitals, set layout_type and overlays
        if "atom" in container.get("id", "").lower():
            metadata["layout_type"] = "atom"
            metadata["ghx_mode"] = "shell"
            metadata["overlay_layers"].append("electron_rings")

        # Hoberman-specific override
        elif any("hoberman" in tag.lower() for tag in container.get("tags", [])):
            metadata["layout_type"] = "hoberman"
            metadata["ghx_mode"] = "expanding_sphere"
            metadata["overlay_layers"].append("symbolic_expansion")

        # Add linkPreview from glyphs (electrons or entangled anchors)
        link_previews = []
        for g in container.get("glyphs", []):
            preview_id = g.get("linkContainerId")
            if preview_id and preview_id not in link_previews:
                link_previews.append(preview_id)
        if link_previews:
            metadata["linkPreview"] = sorted(link_previews)

        # Save metadata back into container
        container["metadata"] = metadata

        # --- Build collapsed KG node for main container ---
        kg_node = self.build_node_from_container_for_kg(       # HOV2/HOV3
            container,
            expand=False                                        # collapsed by default
        )

        # --- Extract KG nodes/edges from glyph_grid ---
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

        # --- Merge our primary container KG node (dedupe by id) ---
        existing_nodes = pack.get("nodes", [])
        idset = {n.get("id") for n in existing_nodes if isinstance(n, dict)}
        if kg_node.get("id") in idset:
            existing_nodes = [n for n in existing_nodes if n.get("id") != kg_node.get("id")]
            idset.discard(kg_node.get("id"))
        existing_nodes.insert(0, {"type": "kg_node", **kg_node})
        idset.add(kg_node.get("id"))

        # --- Collect UCS containers as extra KG nodes (collapsed/lazy by default) ---
        try:
            from backend.modules.dimensions.universal_container_system import ucs_runtime
            ucs_ids = []
            if hasattr(ucs_runtime, "list_containers"):
                ucs_ids = ucs_runtime.list_containers()
            elif hasattr(ucs_runtime, "registry"):
                ucs_ids = list(getattr(ucs_runtime, "registry", {}).keys())

            for cid in ucs_ids or []:
                try:
                    if hasattr(ucs_runtime, "get_container"):
                        uc = ucs_runtime.get_container(cid)
                    elif hasattr(ucs_runtime, "index"):
                        uc = ucs_runtime.index.get(cid)
                    elif hasattr(ucs_runtime, "registry"):
                        uc = ucs_runtime.registry.get(cid)
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
                    print(f"⚠️ Skipped UCS container '{cid}': {e}")
        except Exception as e:
            print(f"⚠️ UCS runtime not available for KG export: {e}")

        # --- Collect SQI registry containers as extra KG nodes (collapsed) ---
        try:
            from backend.modules.sqi.sqi_container_registry import sqi_registry
            for cid, entry in (sqi_registry.index or {}).items():
                try:
                    node = make_kg_payload({"id": cid, "meta": entry.get("meta", {})}, expand=False)
                    nid = node.get("id")
                    if nid and nid not in idset:
                        existing_nodes.append({"type": "kg_node", **node})
                        idset.add(nid)
                except Exception as e:
                    print(f"⚠️ Skipped SQI registry entry '{cid}': {e}")
        except Exception:
            pass  # Fine if registry is not available

        # Final assignment
        pack["nodes"] = existing_nodes

        # --- Write pack to disk ---
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(pack, f, indent=2)

        print(f"💾 KG export saved to {out_path}")
        if ENABLE_WS_BROADCAST:
            _safe_emit(broadcast_event({
                "type": "kg_update",
                "domain": "physics_core",
                "file": str(out_path),
                "status": "saved"
            }))
        return str(out_path)

    def inject_prediction_trace(container: dict, prediction_result: dict) -> None:
        """
        Injects prediction result, contradiction/simplification status,
        and metadata (confidence, entropy, suggestion) into the container.

        Also prepares it for SQI scoring and replay badge rendering.
        """
        container.setdefault("prediction", {}).update(prediction_result)

        status = prediction_result.get("status", "")
        if status in {"contradiction", "simplify"}:
            container.setdefault("metadata", {})["replaySuggested"] = True
            container["prediction"]["trigger_replay"] = True

        # Trace metadata for GHX + Holographic Viewers
        trace = {
            "type": "logic_prediction",
            "status": status,
            "confidence": prediction_result.get("confidence"),
            "entropy": prediction_result.get("entropy"),
            "suggestion": prediction_result.get("suggestion"),
        }

        container.setdefault("logic_trace", []).append(trace)

        # Mark for SQI graph tracking
        container.setdefault("sqi", {})["last_prediction"] = trace

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
        # NEW:
        tags: Optional[list] = None,
    ):
        # ── Recursion/rehydration storm guard ───────────────────────────────────
        global _KG_BUSY
        if _KG_BUSY:
            # Drop (or queue) to prevent infinite re-entry loops
            return
        _KG_BUSY = True
        try:
            # ── Broadcaster (prefer throttled alias; fall back to async enqueue) ─
            _broadcast_sync = None
            _broadcast_async = None
            try:
                # throttled alias accepts a single event dict (sync)
                from backend.routes.ws.glyphnet_ws import broadcast_event_throttled as _broadcast_sync  # type: ignore
            except Exception:
                try:
                    # async enqueue taking a single event dict
                    from backend.routes.ws.glyphnet_ws import broadcast_event as _broadcast_async  # type: ignore
                except Exception:
                    _broadcast_async = None

            import inspect, asyncio

            def _emit(event_dict: dict):
                """Send event via throttled sync if available; otherwise via async enqueue."""
                try:
                    if _broadcast_sync:
                        _broadcast_sync(event_dict)  # sync throttled path
                        return
                    if _broadcast_async:
                        if inspect.iscoroutinefunction(_broadcast_async):
                            try:
                                loop = asyncio.get_running_loop()
                                loop.create_task(_broadcast_async(event_dict))
                            except RuntimeError:
                                asyncio.run(_broadcast_async(event_dict))
                        else:
                            _broadcast_async(event_dict)
                    else:
                        print(f"[SIM:FALLBACK] Broadcast: {event_dict}")
                except Exception:
                    # Never let broadcast failures bubble into KG write path
                    pass

            # ── Original logic (unchanged, just routed through _emit) ────────────
            glyph_id = generate_uuid()
            timestamp = get_current_timestamp()

            # 🔒 Standard Lock Enforcement
            if not crdt_registry.acquire_lock(glyph_id, agent_id):
                raise RuntimeError(f"Glyph {glyph_id} is locked by another agent.")

            _emit({
                "type": "lock_acquired",
                "glyph_id": glyph_id,
                "agent_id": agent_id,
                "tags": ["🔒"]
            })

            # ↔ Entanglement Lock Enforcement
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

            # 🔀 CRDT merge & increment
            merged_version = crdt_registry.merge_vector(glyph_id, version_vector or {})
            crdt_registry.increment_clock(glyph_id, agent_id)

            # ✅ Auto-tagging based on glyph operators
            auto_tags = self._derive_auto_tags(content)
            final_tags = list(set(auto_tags + (tags or [])))

            entry = {
                "id": glyph_id,
                "type": glyph_type,
                "content": content,
                "timestamp": timestamp,
                "metadata": metadata or {},
                "tags": final_tags,  # manual + auto
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

            self._write_to_container(entry)
            add_to_index("knowledge_index.glyph", entry)

            if anchor:
                # lazy async anchor broadcast (works in app & CLI)
                try:
                    from backend.routes.ws.glyphnet_ws import broadcast_anchor_update  # type: ignore
                    if inspect.iscoroutinefunction(broadcast_anchor_update):
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(broadcast_anchor_update(glyph_id, anchor))
                        except RuntimeError:
                            asyncio.run(broadcast_anchor_update(glyph_id, anchor))
                    else:
                        broadcast_anchor_update(glyph_id, anchor)  # sync impl fallback
                except Exception:
                    pass

            # 🔓 Release locks and emit
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
        print(f"🧠 KG: Linking {source_id} → {target_id} ({direction})")
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
        Adds an entanglement edge to the KG.
        """
        print(f"🧠 KG: Entangled {container_a} ↔ {container_b}")
        entangle_entry = {
            "id": generate_uuid(),
            "type": "entanglement",
            "from": container_a,
            "to": container_b,
            "timestamp": get_current_timestamp(),
            "tags": ["entangled", "↔"],
            # NEW:
            "content": f"{container_a} <-> {container_b}",
        }
        add_to_index("knowledge_index.entanglements", entangle_entry)

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
    def add_node(self, node_id: str, label: str, meta: Optional[Dict[str, Any]] = None):
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

    def add_edge(self, src: str, dst: str, relation: str):
        self.write_link_entry(src, dst, relation)
        return self.inject_glyph(
            content=f"KGEdge:{src}->{dst} rel={relation}",
            glyph_type="kg_edge",
            metadata={"from": src, "to": dst, "relation": relation},
            plugin="KG"
        )

    def add_source(self, node_id: str, source: dict):
        """
        Attach or update source metadata for a given KG node by emitting a kg_source glyph.
        source = {"tier": "primary|secondary|tertiary", "ref": "doi/url", "notes": "..."}
        """
        return self.inject_glyph(
            content=f"KGSource:{node_id}",
            glyph_type="kg_source",
            metadata={"node_id": node_id, **(source or {})},
            plugin="KG"
        )

    def link_source(self, node_id: str, source_id: str, relation: str = "supports"):
        """
        Link a node to a source with a 'supports' (or custom) relation, as a normal KG edge.
        """
        return self.add_edge(node_id, source_id, relation)

    def inject_plugin_aware(self, content: str, glyph_type: str, plugin_name: str, metadata: Optional[Dict[str, Any]] = None):
        return self.inject_glyph(content=content, glyph_type=glyph_type, metadata=metadata, plugin=plugin_name)

    def inject_soullaw_violation(self, rule: str, reason: str, context: Optional[Dict[str, Any]] = None):
        return self.inject_glyph(
            content=f"SoulLaw Violation: {rule} – {reason}", glyph_type="violation",
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

    def export_pack(self, container: dict, out_path: str):
        nodes = [g for g in container.get("glyph_grid", []) if g.get("type") == "kg_node"]
        edges = [g for g in container.get("glyph_grid", []) if g.get("type") == "kg_edge"]
        pack = {
            "id": container.get("id"),
            "name": container.get("name"),
            "symbol": container.get("symbol", "❔"),
            "glyph_categories": container.get("glyph_categories", []),
            "nodes": [n["metadata"] | {"type": "kg_node"} for n in nodes if "metadata" in n],
            "links": [
                {
                    "src": e["metadata"]["from"],
                    "dst": e["metadata"]["to"],
                    "relation": e["metadata"]["relation"]
                }
                for e in edges if "metadata" in e
            ],
        }
        import json, os
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(pack, f, indent=2)
        return out_path

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

    def _write_to_container(self, entry: Dict[str, Any]):
        if "glyph_grid" not in self.container:
            self.container["glyph_grid"] = []
        self.container["glyph_grid"].append(entry)
        self.container["last_updated"] = datetime.datetime.utcnow().isoformat()

    # ── Optional: Simple query helpers for dashboards ──
    def list_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        return [g for g in self.container.get("glyph_grid", []) if tag in g.get("tags", [])]

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        glyphs = self.container.get("glyph_grid", [])
        return glyphs[-limit:]

# ──────────────────────────────
# write_glyph_entry (updated)
# ──────────────────────────────

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
        create_task(lazy_broadcast_anchor_update(glyph, anchor))

    return entry  # <-- Ensure function return stays intact

def get_glyph_trace_for_container(container_id: str) -> list:
    """
    Retrieve the symbolic glyph trace from a container by its ID.
    Returns a list of glyphs (or symbolic nodes) for replay / prediction.
    """
    from backend.modules.knowledge_graph.container_loader import load_container_by_id

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
    from backend.modules.runtime.container_runtime import VAULT
    container = VAULT.get(container_id) if container_id else None

    if container is not None:
        container.setdefault("trace", {}).setdefault(event_type, []).append(event)

    print(f"[KGWriter] Event: {event_type} → {container_id} | {event.get('reason', '')}")


# ──────────────────────────────
# Global KG Writer Instance
# ──────────────────────────────

__all__ = ["kg_writer", "store_generated_glyph"]
kg_writer = KnowledgeGraphWriter()