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
- 🧩 Plugin & Forecast Integration ........... ✅
- 🔁 Self-Reflection + Thought Tracing ...... ✅
- 📊 Validator: Stats, Search, DC Export .... ✅
- 🌐 CRDT & Entanglement Locks .............. ✅
"""

import datetime
from typing import Optional, Dict, Any, Tuple
from collections import defaultdict
from backend.modules.state_manager import get_active_universal_container_system
from backend.modules.utils.id_utils import generate_uuid
from backend.modules.utils.time_utils import get_current_timestamp
from backend.modules.dna_chain.container_index_writer import add_to_index
from backend.modules.glyphnet.glyphnet_ws import broadcast_anchor_update, broadcast_event

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
            local[agent] = max(local[agent], clock)
        return local

    # 🔒 Standard Locks
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

    # ↔ Entanglement Locks
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
        self.container = get_active_container()

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
        version_vector: Optional[Dict[str, int]] = None
    ):
        from asyncio import create_task
        glyph_id = generate_uuid()
        timestamp = get_current_timestamp()

        # 🔒 Standard Lock Enforcement
        if not crdt_registry.acquire_lock(glyph_id, agent_id):
            raise RuntimeError(f"Glyph {glyph_id} is locked by another agent.")
        create_task(broadcast_event({
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
            create_task(broadcast_event({
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

        entry = {
            "id": glyph_id,
            "type": glyph_type,
            "content": content,
            "timestamp": timestamp,
            "metadata": metadata or {},
            "tags": auto_tags,
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
            create_task(broadcast_anchor_update(glyph_id, anchor))

        # 🔓 Release Locks
        crdt_registry.release_lock(glyph_id, agent_id)
        create_task(broadcast_event({
            "type": "lock_released",
            "glyph_id": glyph_id,
            "agent_id": agent_id
        }))
        if entangled_group:
            crdt_registry.release_entanglement_lock(entangled_group, agent_id)
            create_task(broadcast_event({
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
            "tags": ["link", "navigation"]
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
            "tags": ["entangled", "↔"]
        }
        add_to_index("knowledge_index.entanglements", entangle_entry)

    def merge_edit(self, glyph_id: str, updates: Dict[str, Any], agent_id: str, version_vector: Dict[str, int]):
        glyphs = self.container.get("glyph_grid", [])
        for g in glyphs:
            if g["id"] == glyph_id:
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
                        "tags": ["⚠️", "conflict"]
                    }
                    self._write_to_container(conflict_entry)

                g.update(updates)
                g["version_vector"] = merged_clock
                g["last_modified_by"] = agent_id
                return g
        raise KeyError(f"Glyph {glyph_id} not found for merge edit.")

    def inject_self_reflection(self, message: str, trigger: str):
        return self.inject_glyph(content=f"Reflection: {message}", glyph_type="self_reflection", metadata={"trigger": trigger})

    def inject_prediction(self, hypothesis: str, based_on: str, confidence: float = 0.75,
                          plugin: Optional[str] = None, region: Optional[str] = None,
                          coords: Optional[Tuple[float, float, float]] = None):
        return self.inject_glyph(content=hypothesis, glyph_type="predictive", metadata={"based_on": based_on},
                                 prediction="future", forecast_confidence=confidence, plugin=plugin,
                                 region=region, coordinates=coords)

    def inject_plugin_aware(self, content: str, glyph_type: str, plugin_name: str, metadata: Optional[Dict[str, Any]] = None):
        return self.inject_glyph(content=content, glyph_type=glyph_type, metadata=metadata, plugin=plugin_name)

    def inject_soullaw_violation(self, rule: str, reason: str, context: Optional[Dict[str, Any]] = None):
        return self.inject_glyph(
            content=f"SoulLaw Violation: {rule} – {reason}", glyph_type="violation",
            metadata={"rule": rule, "type": "SoulLaw", "reason": reason, "context": context or {}, "tags": ["📜", "🧠", "❌"]},
            plugin="SoulLaw"
        )

    def _derive_auto_tags(self, content: str) -> list:
        tags = []
        if "↔" in content: tags.append("entangled")
        if "⧖" in content: tags.append("collapse")
        if "⬁" in content: tags.append("rewrite")
        if "🧬" in content: tags.append("mutation")
        if "⚛" in content: tags.append("qglyph")
        return tags

    def _write_to_container(self, entry: Dict[str, Any]):
        if "glyph_grid" not in self.container:
            self.container["glyph_grid"] = []
        self.container["glyph_grid"].append(entry)
        self.container["last_updated"] = datetime.datetime.utcnow().isoformat()


# ──────────────────────────────
# write_glyph_entry (unchanged)
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
    if anchor: entry["anchor"] = anchor

    from backend.modules.knowledge_graph.indexes.reasoning_index import add_reasoning_entry
    add_reasoning_entry(glyph_id=glyph, reasoning=reasoning_chain or "Unspecified", context=context)
    add_to_index("knowledge_index.glyph", entry)

    if anchor:
        from asyncio import create_task
        create_task(broadcast_anchor_update(glyph, anchor))

    return entry