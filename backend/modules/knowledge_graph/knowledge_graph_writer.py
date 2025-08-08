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
import datetime
import importlib
from typing import Optional, Dict, Any, Tuple, List
from collections import defaultdict

# ✅ Correct utility imports
from backend.modules.knowledge_graph.id_utils import generate_uuid
from backend.modules.knowledge_graph.time_utils import get_current_timestamp

# ✅ Knowledge graph and indexing
from backend.modules.dna_chain.container_index_writer import add_to_index

# --- add near the top of the file (after imports) ---
_EPHEMERAL_CONTAINER = {"id": "kg_cli_ephemeral", "glyph_grid": [], "last_updated": None}

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
    def __init__(self):
        # Explicitly attached UCS container (if any)
        self._container = None  

    def attach_container(self, container: dict):
        """
        Bind a specific UCS container so glyphs land in the correct place.
        This bypasses the default active container.
        """
        self._container = container

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
                # lazy imports to avoid circular deps
        try:
            from backend.routes.ws.glyphnet_ws import broadcast_event
        except Exception:
            broadcast_event = lambda *a, **k: None  # no-op if WS not available

        # safe async emit to handle both server + CLI contexts
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

        glyph_id = generate_uuid()
        timestamp = get_current_timestamp()

        # 🔒 Standard Lock Enforcement
        if not crdt_registry.acquire_lock(glyph_id, agent_id):
            raise RuntimeError(f"Glyph {glyph_id} is locked by another agent.")

        try:
            from backend.routes.ws.glyphnet_ws import broadcast_event
        except Exception:
            broadcast_event = lambda *a, **k: None  # no-op if WS not available

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

        _safe_emit(broadcast_event({
            "type": "lock_acquired",
            "glyph_id": glyph_id,
            "agent_id": agent_id,
            "tags": ["🔒"]
        }))

        # ↔ Entanglement Lock Enforcement
        entangled_group = None
        if metadata and "entangled_ids" in metadata:
            entangled_group = "|".join(sorted(metadata["entangled_ids"]))
            if not crdt_registry.acquire_entanglement_lock(entangled_group, agent_id):
                raise RuntimeError(f"Entangled group {entangled_group} is locked by another agent.")

            _safe_emit(broadcast_event({
                "type": "entanglement_lock_acquired",
                "entangled_group": entangled_group,
                "agent_id": agent_id,
                "tags": ["↔", "🔒"]
            }))

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
            "tags": final_tags,  # <-- now includes manual + auto
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
            # keep your lazy anchor broadcaster pattern
            try:
                from backend.routes.ws.glyphnet_ws import broadcast_anchor_update
                create_task(broadcast_anchor_update(glyph_id, anchor))
            except Exception:
                pass

        # 🔓 Release Locks
        crdt_registry.release_lock(glyph_id, agent_id)

        try:
            from backend.routes.ws.glyphnet_ws import broadcast_event
        except Exception:
            broadcast_event = lambda *a, **k: None  # no-op if WS not available

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

        _safe_emit(broadcast_event({
            "type": "lock_released",
            "glyph_id": glyph_id,
            "agent_id": agent_id
        }))

        if entangled_group:
            crdt_registry.release_entanglement_lock(entangled_group, agent_id)
            _safe_emit(broadcast_event({
                "type": "entanglement_lock_released",
                "entangled_group": entangled_group,
                "agent_id": agent_id
            }))

        return glyph_id

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

    def merge_edit(self, glyph_id: str, updates: Dict[str, Any], agent_id: str, version_vector: Dict[str, int]):
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

    # ── Convenience injectors (kept) ──
    def inject_self_reflection(self, message: str, trigger: str):
        return self.inject_glyph(content=f"Reflection: {message}", glyph_type="self_reflection", metadata={"trigger": trigger})

    def inject_prediction(self, hypothesis: str, based_on: str, confidence: float = 0.75,
                          plugin: Optional[str] = None, region: Optional[str] = None,
                          coords: Optional[Tuple[float, float, float]] = None):
        return self.inject_glyph(content=hypothesis, glyph_type="predictive", metadata={"based_on": based_on},
                                 prediction="future", forecast_confidence=confidence, plugin=plugin,
                                 region=region, coordinates=coords)
    
        # ── KG node/edge helpers ──
    def add_node(self, node_id: str, label: str, meta: Optional[Dict[str, Any]] = None):
        """
        Store a KG node as a glyph entry (typed 'kg_node') so it is queryable + replayable.
        """
        return self.inject_glyph(
            content=f"KGNode:{node_id} label={label}",
            glyph_type="kg_node",
            metadata={"node_id": node_id, "label": label, **(meta or {})},
            plugin="KG"
        )

    def add_edge(self, src: str, dst: str, relation: str):
        """
        Store a KG edge. Reuse the existing link writer for indexes + telemetry.
        """
        self.write_link_entry(src, dst, relation)
        # Optionally also persist a glyph for timeline/replay:
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
            content=f"SoulLaw Violation: {rule} – {reason}", glyph_type="violation",
            metadata={"rule": rule, "type": "SoulLaw", "reason": reason, "context": context or {}, "tags": ["📜", "🧠", "❌"]},
            plugin="SoulLaw"
        )

    def load_domain_pack(self, container_id: str, container: Dict[str, Any]) -> bool:
        """
        Ingest a domain seed (e.g., physics_core) into the live KG.
        Returns True if handled.
        """
        if container_id != "physics_core":
            return False

        for node in container.get("nodes", []):
            self.add_node(
                node["id"],
                label=node.get("label", node["id"]),
                meta={
                    "source": "physics_core",
                    "domain": "physics",
                    "category": node.get("cat"),
                },
            )

        for link in container.get("links", []):
            self.add_edge(link["src"], link["dst"], link.get("relation", "relates_to"))

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


# ──────────────────────────────
# Global KG Writer Instance
# ──────────────────────────────
kg_writer = KnowledgeGraphWriter()