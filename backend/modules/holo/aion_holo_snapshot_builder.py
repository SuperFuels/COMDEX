# backend/modules/holo/aion_holo_snapshot_builder.py

"""
Builder: AION memory + rulebook seeds → single HoloIR-style snapshot.

This does NOT write anything to disk.
It just returns a dict shaped like HoloIR so existing frontend
(HologramContainerView / DevFieldHologram3DContainer) can render it.
"""

from __future__ import annotations

import time
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Sequence

from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.holo.aion_memory_holo_adapter import (
    HoloSeed,
    AION_MEMORY_CONTAINER_ID,
)
from backend.modules.holo.rulebook_holo_adapter import (
    RuleBookHoloSeed,
    RULEBOOK_CONTAINER_ID,
)

DNA_SWITCH.register(__file__)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _short(text: str, max_len: int = 72) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _seed_to_ghx_node_from_memory(seed: HoloSeed, index: int) -> Dict[str, Any]:
    payload = seed.payload or {}
    label = payload.get("label") or seed.label or "memory"
    tags = list(seed.tags or [])
    ts = payload.get("timestamp") or seed.created_at

    return {
        "id": seed.seed_id,
        "label": _short(str(label)),
        "type": "aion_memory",
        "tags": tags,
        "pos": None,  # DevFieldHologram3DContainer will ignore + recompute layout
        "icon": "🧠" if index == 0 else "•",
        "meta": {
            "kind": "memory_entry",
            "timestamp": ts,
            "container_id": AION_MEMORY_CONTAINER_ID,
            "index": index,
        },
    }


def _seed_to_ghx_node_from_rulebook(seed: RuleBookHoloSeed, index: int) -> Dict[str, Any]:
    payload = seed.payload or {}
    rb_id = payload.get("rulebook_id") or seed.rulebook_id
    name = payload.get("name") or rb_id
    tags = list(seed.tags or [])
    metrics = payload.get("metrics") or {}

    return {
        "id": seed.seed_id,
        "label": _short(str(name)),
        "type": "aion_rulebook",
        "tags": tags,
        "pos": None,
        "icon": "📜",
        "meta": {
            "kind": "rulebook",
            "rulebook_id": rb_id,
            "usage_count": seed.usage_count,
            "metrics": metrics,
            "container_id": RULEBOOK_CONTAINER_ID,
            "index": index,
        },
    }


def _sequence_edges_for_nodes(node_ids: Sequence[str], base_id: str) -> List[Dict[str, Any]]:
    """
    Simple chain edges: n0 → n1 → n2 ... so the hologram isn't totally empty.
    """
    edges: List[Dict[str, Any]] = []
    for i in range(len(node_ids) - 1):
        src = node_ids[i]
        dst = node_ids[i + 1]
        edges.append(
            {
                "id": f"{base_id}:seq:{i}",
                "src": src,
                "dst": dst,
                # DevFieldHologram3DContainer will also map source/target fields
                "source": src,
                "target": dst,
                "relation": "sequence",
                "weight": 1.0,
                "tags": ["sequence"],
                "meta": {
                    "kind": "sequence",
                    "index": i,
                },
                "data": {
                    "relation": "sequence",
                    "from": "aion_holo_snapshot_builder",
                },
            }
        )
    return edges


def _entanglement_edges_between_memory_and_rulebooks(
    memory_nodes: Sequence[Dict[str, Any]],
    rulebook_nodes: Sequence[Dict[str, Any]],
    base_id: str,
) -> List[Dict[str, Any]]:
    """
    Build light-weight 'entanglement' edges based on overlapping tags
    between memory entries and rulebooks.
    """
    edges: List[Dict[str, Any]] = []
    eid = 0

    for m in memory_nodes:
        mtags = set(m.get("tags") or [])
        if not mtags:
            continue

        for r in rulebook_nodes:
            rtags = set(r.get("tags") or [])
            if not rtags:
                continue

            overlap = mtags.intersection(rtags)
            if not overlap:
                continue

            src = m["id"]
            dst = r["id"]
            edges.append(
                {
                    "id": f"{base_id}:ent:{eid}",
                    "src": src,
                    "dst": dst,
                    "source": src,
                    "target": dst,
                    "relation": "entangled",
                    "weight": float(len(overlap)),
                    "tags": ["entangled"] + sorted(overlap),
                    "meta": {
                        "kind": "entangled",
                        "overlap_tags": sorted(overlap),
                    },
                    "data": {
                        "relation": "entangled",
                        "from": "aion_holo_snapshot_builder",
                    },
                }
            )
            eid += 1

    return edges


def build_memory_rulebook_holo_snapshot(
    memory_seeds: List[HoloSeed],
    rulebook_seeds: List[RuleBookHoloSeed],
) -> Dict[str, Any]:
    """
    Pack AION memory + rulebook seeds into a single HoloIR-shaped dict.

    This is intentionally minimal:
      - ghx.nodes = memory nodes + rulebook nodes
      - ghx.edges = simple sequences + entanglement edges
      - metadata carries enough context for DevTools.
    """
    created_at = _now_iso()
    tick = 0  # later we can thread through real timefold ticks
    rev = 1   # for now treat as v1 preview

    # stable-ish holo_id: holo:container/<cid>/t=<tick>/v<rev>
    holo_id = f"holo:container/aion_memory_field/t={tick}/v{rev}"

    memory_nodes = [
      _seed_to_ghx_node_from_memory(seed, idx) for idx, seed in enumerate(memory_seeds)
    ]
    rulebook_nodes = [
      _seed_to_ghx_node_from_rulebook(seed, idx) for idx, seed in enumerate(rulebook_seeds)
    ]

    all_nodes = memory_nodes + rulebook_nodes
    node_ids = [n["id"] for n in all_nodes]

    base_edge_id = f"{holo_id}:edges"

    seq_edges = _sequence_edges_for_nodes(node_ids, base_edge_id + ":all")
    ent_edges = _entanglement_edges_between_memory_and_rulebooks(
        memory_nodes, rulebook_nodes, base_edge_id + ":mr"
    )

    ghx = {
        "ghx_version": "1.0",
        "origin": "aion_holo_snapshot_builder",
        "container_id": "aion_memory_field",
        "nodes": all_nodes,
        "edges": seq_edges + ent_edges,
        "metadata": {
            "snapshot_kind": "aion_memory+rulebook_field",
        },
    }

    # HoloIR-shaped dict
    holo: Dict[str, Any] = {
        "holo_id": holo_id,
        "container_id": "aion_memory_field",
        "kind": "aion_memory_field",
        "created_at": created_at,
        "timefold": {
            "tick": tick,
            "frame": "memory_field",
        },
        "indexing": {
            "source": "aion_holo_snapshot_builder",
            "tags": ["aion", "memory", "rulebook"],
        },
        "ghx": ghx,
        "metadata": {
            "memory_container_id": AION_MEMORY_CONTAINER_ID,
            "rulebook_container_id": RULEBOOK_CONTAINER_ID,
            "memory_count": len(memory_seeds),
            "rulebook_count": len(rulebook_seeds),
            "built_at": created_at,
            "built_unix": time.time(),
        },
    }

    return holo