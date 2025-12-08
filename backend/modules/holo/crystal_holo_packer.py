# backend/modules/holo/crystal_holo_packer.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.modules.holo.crystal_motifs import Motif
from backend.modules.holo.crystal_container import CrystalContainer


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def pack_crystal_holo(
    motif: Motif,
    container: CrystalContainer,
    tick: int,
    revision: int = 1,
) -> Dict[str, Any]:
    """
    Turn a Motif into a compact HoloIR "habit crystal".

    Graph structure:
      - core node: one "crystal" node with pattern_strength, sqi, usage
      - one node per step
      - edges:
          core → step[i]
          step[i] → step[i+1]   (sequence)
    """

    container_id = container.container_id
    holo_id = f"holo:{container_id}:motif={motif.motif_id}/t={tick}/v={revision}"
    crystal_uri = container.make_crystal_uri(motif.motif_id, tick, revision)

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    core_id = f"crystal:{motif.motif_id}"

    # Core crystal node
    nodes.append(
        {
            "id": core_id,
            "data": {
                "label": motif.label,
                "symbol": "✦",
                "type": "crystal",
                "kind": "habit_crystal",
                "pattern_strength": motif.metrics.get("strength", motif.strength),
                "support": motif.metrics.get("support", motif.support),
                "sqi": motif.sqi,
                "tags": motif.tags,
                "created_at": _iso_now(),
            },
        }
    )

    # Step nodes
    step_ids: List[str] = []
    for idx, step in enumerate(motif.steps):
        sid = f"{core_id}::step:{idx}"
        step_ids.append(sid)

        nodes.append(
            {
                "id": sid,
                "data": {
                    "label": step,
                    "symbol": "●",
                    "type": "crystal_step",
                    "step_index": idx,
                    "parent_crystal": core_id,
                    "tags": ["crystal-step"],
                },
            }
        )

        # edge from core to step
        edges.append(
            {
                "id": f"{core_id}::{sid}",
                "source": core_id,
                "target": sid,
                "kind": "crystal_step",
            }
        )

    # Sequential edges between steps
    for i in range(len(step_ids) - 1):
        a = step_ids[i]
        b = step_ids[i + 1]
        edges.append(
            {
                "id": f"{a}::{b}",
                "source": a,
                "target": b,
                "kind": "crystal_flow",
            }
        )

    ghx = {
        "ghx_version": "1.0",
        "origin": "crystal_holo_packer",
        "container_id": container_id,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "pattern_strength": motif.strength,
            "support": motif.support,
            "sqi": motif.sqi,
        },
    }

    holo: Dict[str, Any] = {
        "holo_id": holo_id,
        "container_id": container_id,
        "tick": tick,
        "revision": revision,
        "created_at": _iso_now(),
        "ghx_mode": "snapshot",
        "ghx": ghx,
        "psi_kappa_tau_signature": {
            # simple defaults; can be refined later
            "psi": motif.strength,
            "kappa": 0.0,
            "tau": 0.0,
            "energy": motif.metrics.get("support", motif.support),
            "entropy": 1.0,
            "rank": 1,
        },
        "metadata": {
            "kind": "habit_crystal",
            "crystal": {
                "uri": crystal_uri,
                "motif_id": motif.motif_id,
                "label": motif.label,
                "owner_kind": container.owner_kind,
                "owner_id": container.owner_id,
                "pattern_strength": motif.strength,
                "support": motif.support,
                "sqi": motif.sqi,
                "metrics": motif.metrics,
                "tags": motif.tags,
            },
        },
    }

    return holo


def build_and_save_crystal(
    motif: Motif,
    owner_kind: str = "user",
    owner_id: str = "devtools",
    revision: int = 1,
) -> Dict[str, Any]:
    """
    Convenience helper:

      motif → CrystalContainer.for_owner(...) → pack_crystal_holo → save

    Returns the holo with a storage hint in metadata.
    """
    container = CrystalContainer.for_owner(owner_kind, owner_id)
    tick = container.next_tick()

    holo = pack_crystal_holo(
        motif=motif,
        container=container,
        tick=tick,
        revision=revision,
    )

    path = container.save_crystal_holo(holo)

    meta = holo.setdefault("metadata", {})
    storage = meta.setdefault("storage", {})
    storage["path"] = str(path)

    return holo