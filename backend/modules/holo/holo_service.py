# backend/modules/holo/holo_service.py
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone

from backend.modules.holo.holo_ir import HoloIR

# Optional deps – we’ll fail soft if they’re missing / limited
try:
    from backend.modules.knowledge_graph.knowledge_graph_writer import kg_writer as _kg_writer
except Exception:
    _kg_writer = None

try:
    from backend.modules.glyphwave.qwave.qwave_writer import collect_qwave_beams as _collect_qwave_beams
except Exception:
    _collect_qwave_beams = None

try:
    from backend.modules.dna_chain.container_index_writer import add_to_index as _add_to_index
except Exception:
    _add_to_index = None

# Where .holo JSONs are written
HOLO_ROOT = Path("backend/modules/dimensions/containers/holo_exports")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_holo_id(container_id: str, tick: int, revision: int = 1) -> str:
    return f"holo:container/{container_id}/t={tick}/v{revision}"


def _load_kg_pack(container_id: str):
    """
    Best-effort KG export for GHX.
    Falls back to an empty pack if writer or method is missing.
    """
    pack: Dict[str, Any] = {
        "nodes": [],
        "links": [],
        "qwave": {},
    }
    pack_path = None

    if not _kg_writer:
        print("[HOLO] kg_writer not available; using empty GHX pack.")
        return pack, pack_path

    try:
        # Variant 1: save_pack_for_container(cid) -> path (JSON)
        if hasattr(_kg_writer, "save_pack_for_container"):
            pack_path = _kg_writer.save_pack_for_container(container_id)
            with open(pack_path, "r", encoding="utf-8") as f:
                pack = json.load(f)
            return pack, pack_path

        # Variant 2: export_pack_for_container(cid) -> dict
        if hasattr(_kg_writer, "export_pack_for_container"):
            pack = _kg_writer.export_pack_for_container(container_id)
            return pack, None

        print("[HOLO] kg_writer has no pack export method; using empty GHX pack.")
        return pack, None

    except Exception as e:
        print(f"[HOLO] KG pack export failed for {container_id}: {e}")
        return pack, None


def _load_beams(container_id: str, pack: Dict[str, Any]):
    """
    Prefer beams already embedded in the KG pack; otherwise,
    try QWave writer; otherwise, return [].
    """
    # from pack
    beams = (
        pack.get("qwave", {}).get("beams")
        or pack.get("beams")
        or []
    )

    if beams:
        return beams

    # fallback: live collection
    if _collect_qwave_beams:
        try:
            return _collect_qwave_beams(container_id) or []
        except Exception as e:
            print(f"[HOLO] collect_qwave_beams failed for {container_id}: {e}")

    return []


def export_holo_from_container(
    container: Dict[str, Any],
    view_ctx: Dict[str, Any],
    revision: int = 1,
) -> HoloIR:
    """
    Core export: container + view_ctx -> HoloIR + .holo JSON on disk.
    Best-effort; never raises just because KG/QWave/indexing is missing.
    """
    cid = container.get("id", "unknown")
    tick = int(view_ctx.get("tick", 0))

    holo_id = _make_holo_id(cid, tick, revision)

    # 1) GHX pack (graph) – best-effort
    pack, pack_path = _load_kg_pack(cid)

    # 2) QWave beams – from pack or live
    beams = _load_beams(cid, pack)

    # 3) Field metrics (either from view_ctx or a safe default)
    metrics = view_ctx.get("metrics") or {
        "coherence": 1.0,
        "drift": 0.0,
        "tick": tick,
    }

    # 4) Build HoloIR object
    holo = HoloIR(
        holo_id=holo_id,
        container_id=cid,
        name=container.get("name"),
        symbol=container.get("symbol"),
        kind=view_ctx.get("kind", "memory"),
        origin={
            "created_at": _utc_now_iso(),
            "created_by": view_ctx.get("created_by", "aion"),
            "reason": view_ctx.get("reason", "export_from_devtools"),
            "source_view": view_ctx.get("source_view", "qfc"),
        },
        version={
            "major": 0,
            "minor": 1,
            "patch": 0,
            "revision": revision,
        },
        ghx={
            "nodes": pack.get("nodes", []),
            "edges": pack.get("links", []),
            "layout": container.get("metadata", {}).get("layout_type"),
            "ghx_mode": container.get("metadata", {}).get("ghx_mode", "hologram"),
            "overlay_layers": container.get("metadata", {}).get("overlay_layers", []),
            "entangled_links": container.get("metadata", {}).get("entangled_links", []),
        },
        field={
            "psi_kappa_T": {
                "frame": view_ctx.get("frame", "original"),
                "state_vector": view_ctx.get("psi_state") or {},
            },
            "metrics": metrics,
        },
        beams=beams,
        multiverse_frame=view_ctx.get("frame", "original"),
        views=view_ctx.get("views", {}),
        indexing={
            "tags": view_ctx.get("tags", []),
            "patterns": view_ctx.get("patterns", []),
            "topic_vector": view_ctx.get("topic_vector"),
        },
        timefold={
            "tick": tick,
            "t_label": view_ctx.get("t_label"),
        },
        references={
            "container_kg_export": str(pack_path) if pack_path else None,
            "container_dc_path": view_ctx.get("container_dc_path"),
        },
    )

    # 5) Persist .holo JSON (ensure directory)
    out_dir = HOLO_ROOT / cid
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{holo_id.replace(':', '_').replace('/', '_')}.holo.json"

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(holo.__dict__, f, indent=2)
        print(f"[HOLO] Exported HoloIR → {out_path}")
    except Exception as e:
        print(f"[HOLO] Failed to write HoloIR file for {cid}: {e}")

    # 6) Optional: index entry in KG (best-effort)
    if _add_to_index:
        try:
            _add_to_index(
                "knowledge_index.holo",
                {
                    "id": holo_id,
                    "type": "holo",
                    "content": {"path": str(out_path)},
                    "timestamp": _utc_now_iso(),
                    "metadata": {
                        "container_id": cid,
                        "tick": tick,
                        "tags": holo.indexing.get("tags", []),
                    },
                },
            )
        except Exception as e:
            print(f"[HOLO] add_to_index failed for {holo_id}: {e}")
    else:
        print("[HOLO] add_to_index not available; skipping holo index.")

    return holo


def load_holo(holo_path: str) -> HoloIR:
    with open(holo_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return HoloIR(**data)