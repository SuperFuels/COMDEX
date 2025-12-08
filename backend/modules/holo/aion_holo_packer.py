# backend/modules/holo/aion_holo_packer.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.modules.holo.aion_holo_memory import get_combined_holo_seeds


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def pack_aion_memory_holo(
    limit_memory: int = 64,
    *,
    tick: int = 0,
    revision: int = 1,
) -> Dict[str, Any]:
    """
    Build a HoloIR-style snapshot for the AION memory field.

    - Loads combined memory + rulebook seeds
    - Maps each seed → GHX node
    - Connects everything to the central 'aion-core' node
    """

    combined = get_combined_holo_seeds(limit_memory=limit_memory)
    memory = combined.get("memory", []) or []
    rulebooks = combined.get("rulebooks", []) or []

    container_id = "aion_memory::core"

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # ── core node
    core_id = "aion-core"
    nodes.append(
        {
            "id": core_id,
            "data": {
                "label": "AION Core",
                "symbol": "A",
                "type": "core",
            },
        }
    )

    # ── memory seeds → nodes + edges
    for seed in memory:
        sid = seed.get("seed_id", "mem-unknown")
        payload = seed.get("payload", {}) or {}
        metrics = payload.get("metrics", {}) or {}

        nodes.append(
            {
                "id": sid,
                "data": {
                    "label": seed.get("label")
                    or payload.get("label")
                    or sid,
                    "symbol": "●",
                    "type": "memory",
                    "tags": seed.get("tags", []),
                    "source": payload.get("source", "MemoryEngine"),
                    "created_at": seed.get("created_at"),
                    "metrics": metrics,
                },
            }
        )

        edges.append(
            {
                "id": f"{core_id}::{sid}",
                "source": core_id,
                "target": sid,
                "kind": "memory",
            }
        )

    # ── rulebook seeds → nodes + edges
    for seed in rulebooks:
        sid = seed.get("seed_id", "rulebook-unknown")
        payload = seed.get("payload", {}) or {}
        metrics = payload.get("metrics", {}) or {}

        nodes.append(
            {
                "id": sid,
                "data": {
                    "label": payload.get("name") or seed.get("rulebook_id", sid),
                    "symbol": "◆",
                    "type": "rulebook",
                    "tags": seed.get("tags", []),
                    "rulebook_id": seed.get("rulebook_id"),
                    "created_at": seed.get("created_at"),
                    "updated_at": seed.get("updated_at"),
                    "usage_count": seed.get("usage_count"),
                    "metrics": metrics,
                    "domains": payload.get("domains", []),
                },
            }
        )

        edges.append(
            {
                "id": f"{core_id}::rule::{sid}",
                "source": core_id,
                "target": sid,
                "kind": "rulebook",
            }
        )

    ghx = {
        "ghx_version": "1.0",
        "origin": "aion_memory_holo_packer",
        "container_id": container_id,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "memory_seed_count": len(memory),
            "rulebook_seed_count": len(rulebooks),
        },
    }

    holo_id = f"holo:aion_memory::t={tick}/v={revision}"

    holo = {
        "holo_id": holo_id,
        "container_id": container_id,
        "tick": tick,
        "revision": revision,
        "created_at": _iso_now(),
        "ghx_mode": "snapshot",
        "ghx": ghx,
        "psi_kappa_tau_signature": {
            "psi": 1.0,
            "kappa": 0.0,
            "tau": 0.0,
            "energy": 1.0,
            "entropy": 1.0,
            "rank": 1,
        },
        "metadata": {
            "kind": "aion_memory_snapshot",
            "container": {
                "container_id": container_id,
                "title": "AION Memory Field",
                "description": (
                    "Live constellation of AION's recent personal memories and "
                    "active rulebooks, packed into a single hologram."
                ),
                "memory_seeds": memory,
                "rulebook_seeds": rulebooks,
                "layout": {
                    "kind": "aion_memory_constellation",
                    "version": 1,
                    "slots": {
                        "memory": {
                            "max_cards": 64,
                            "placement": "inner_ring",
                            "priority": "recent_milestones_first",
                        },
                        "rulebooks": {
                            "max_cards": 16,
                            "placement": "outer_ring",
                            "priority": "usage_count_desc",
                        },
                    },
                    "labels": {
                        "memory": "AION recent memories",
                        "rulebooks": "Active rulebooks",
                    },
                },
            },
        },
    }

    return holo