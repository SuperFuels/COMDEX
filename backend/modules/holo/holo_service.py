# backend/modules/holo/holo_service.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import glob
import os

from backend.modules.holo.holo_ir import HoloIR
# Optional deps – we’ll fail soft if they’re missing / limited
try:
    from backend.modules.knowledge_graph.knowledge_graph_writer import (
        kg_writer as _kg_writer,
    )
except Exception:
    _kg_writer = None

try:
    from backend.modules.glyphwave.qwave.qwave_writer import (
        collect_qwave_beams as _collect_qwave_beams,
    )
except Exception:
    _collect_qwave_beams = None

try:
    from backend.modules.dna_chain.container_index_writer import (
        add_to_index as _add_to_index,
    )
except Exception:
    _add_to_index = None

# Where .holo JSONs are written
HOLO_ROOT = Path("backend/modules/dimensions/containers/holo_exports")

# Simple on-disk index for all holos (global, across containers)
HOLO_INDEX_PATH = HOLO_ROOT / "holo_index.json"


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


# -------------------------------------------------------------------
# Holo index (.holo_index.json) helpers
# -------------------------------------------------------------------


@dataclass
class HoloIndexEntry:
    container_id: str
    holo_id: str
    revision: int
    tick: int
    created_at: str  # ISO-8601
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _load_holo_index() -> List[Dict[str, Any]]:
    if not HOLO_INDEX_PATH.exists():
        return []
    try:
        return json.loads(HOLO_INDEX_PATH.read_text())
    except Exception:
        # corrupt index should not crash exports
        return []


def _write_holo_index(entries: List[Dict[str, Any]]) -> None:
    HOLO_INDEX_PATH.write_text(json.dumps(entries, indent=2, sort_keys=True))


def add_to_holo_index(entry: HoloIndexEntry) -> None:
    """
    Upsert a single HoloIndexEntry by holo_id.
    """
    entries = _load_holo_index()
    entries = [e for e in entries if e.get("holo_id") != entry.holo_id]
    entries.append(entry.to_dict())
    _write_holo_index(entries)


def load_holo_history_for_container(container_id: str) -> List[Dict[str, Any]]:
    """
    Return all index entries for a container, newest first.
    """
    entries = _load_holo_index()
    entries = [e for e in entries if e.get("container_id") == container_id]

    entries.sort(
        key=lambda e: (
            e.get("tick", 0),
            e.get("revision", 0),
            e.get("created_at", ""),
        ),
        reverse=True,
    )
    return entries

def load_holo_history_for_container(container_id: str) -> List[Dict[str, Any]]:
    """
    Return all index entries for a container, newest first.
    """
    entries = _load_holo_index()
    entries = [e for e in entries if e.get("container_id") == container_id]

    entries.sort(
        key=lambda e: (
            e.get("tick", 0),
            e.get("revision", 0),
            e.get("created_at", ""),
        ),
        reverse=True,
    )
    return entries


def search_holo_index(
    container_id: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Global search over holo_index.json.

    Filters:
      - container_id (optional)
      - tag (optional, must be in entry.tags)
    Returns newest → oldest.
    """
    entries = _load_holo_index()

    if container_id:
        entries = [e for e in entries if e.get("container_id") == container_id]

    if tag:
        entries = [e for e in entries if tag in (e.get("tags") or [])]

    entries.sort(
        key=lambda e: (
            e.get("tick", 0),
            e.get("revision", 0),
            e.get("created_at", ""),
        ),
        reverse=True,
    )
    return entries

# -------------------------------------------------------------------
# Export: container → HoloIR + .holo file (+ index updates)
# -------------------------------------------------------------------
def _persist_holo(holo: HoloIR) -> HoloIR:
    """
    Common persistence helper: write .holo JSON and return the object.
    """
    cid = holo.container_id or "unknown"
    out_dir = HOLO_ROOT / cid
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_id = holo.holo_id.replace(":", "_").replace("/", "_")
    out_path = out_dir / f"{safe_id}.holo.json"

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(holo.__dict__, f, indent=2)

    return holo


def save_holo_from_dict(payload: Dict[str, Any]) -> HoloIR:
    """
    Build a HoloIR from a minimal dict (e.g. motif compiler output)
    and persist it as a .holo snapshot.

    Required keys: holo_id, container_id, ghx.
    Everything else is optional and defaulted.
    """
    if "holo_id" not in payload or "container_id" not in payload:
        raise ValueError("holo_id and container_id are required")

    ghx = payload.get("ghx") or {}
    metadata = payload.get("metadata") or ghx.get("metadata") or {}

    holo = HoloIR(
        holo_id=payload["holo_id"],
        container_id=payload["container_id"],
        name=payload.get("name"),
        symbol=payload.get("symbol"),
        kind=payload.get("kind") or "crystal_motif",
        origin=payload.get("origin") or {"source": "motif_compile"},
        version=payload.get("version") or {"schema": "1.0"},
        ghx=ghx,
        field=payload.get("field") or {},
        beams=payload.get("beams") or [],
        multiverse_frame=payload.get("multiverse_frame"),
        views=payload.get("views") or {},
        indexing=payload.get("indexing") or {},
        timefold=payload.get("timefold") or {},
        ledger=payload.get("ledger") or {},
        security=payload.get("security") or {},
        sandbox=payload.get("sandbox") or {},
        collaboration=payload.get("collaboration") or {},
        references=payload.get("references") or {},
        extra=payload.get("extra") or {"motif_metadata": metadata},
    )

    return _persist_holo(holo)

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
            "overlay_layers": container.get("metadata", {}).get(
                "overlay_layers", []
            ),
            "entangled_links": container.get("metadata", {}).get(
                "entangled_links", []
            ),
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

    # 7) Update holo_index.json (C1F) – best-effort
    try:
        version = getattr(holo, "version", None) or {}
        timefold = getattr(holo, "timefold", None) or {}
        origin = getattr(holo, "origin", None) or {}
        indexing = getattr(holo, "indexing", None) or {}

        revision_val = version.get("revision", 1)
        tick_val = timefold.get("tick", 0)
        created_at = origin.get("created_at") or _utc_now_iso()
        tags = indexing.get("tags", []) or []

        idx_entry = HoloIndexEntry(
            container_id=holo.container_id,
            holo_id=holo.holo_id,
            revision=int(revision_val),
            tick=int(tick_val),
            created_at=created_at,
            tags=tags,
        )
        add_to_holo_index(idx_entry)
    except Exception as e:
        # Index errors should not break export – just log
        print(f"[holo_index] failed to update index for {holo.holo_id}: {e}")

    return holo


# -------------------------------------------------------------------
# Load helpers (latest / specific / index)
# -------------------------------------------------------------------


def load_holo(holo_path: str) -> HoloIR:
    with open(holo_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return HoloIR(**data)


def _find_holo_paths_for_container(container_id: str) -> List[Path]:
    """
    Internal helper: find all .holo.json files for a container.

    Supports both:
      - nested: HOLO_ROOT/<cid>/*.holo.json
      - flat/legacy: HOLO_ROOT/*<cid>*.holo.json
    """
    root: Path = HOLO_ROOT

    # 1) nested dir exports: backend/modules/dimensions/containers/holo_exports/<cid>/*.holo.json
    pattern1 = root / container_id / "*.holo.json"
    # 2) legacy / flat exports in holo_exports root: *<cid>*.holo.json
    pattern2 = root / f"*{container_id}*.holo.json"

    candidates: List[Path] = [
        Path(p)
        for pat in (pattern1, pattern2)
        for p in glob.glob(str(pat))
    ]

    # newest first by mtime
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def load_latest_holo_for_container(container_id: str) -> Optional[HoloIR]:
    """
    Return the most recent HoloIR for this container, or None if none exist.
    """
    paths = _find_holo_paths_for_container(container_id)
    if not paths:
        return None

    latest_path = paths[0]
    try:
        return load_holo(str(latest_path))
    except Exception as e:
        print(f"[HOLO] load_latest_holo_for_container failed for {container_id}: {e}")
        return None


def load_holo_index_for_container(container_id: str) -> List[Dict[str, Any]]:
    """
    Lightweight index of all holo snapshots for a container (from files).

    Returns a list of entries with:
      - holo_id
      - container_id
      - tick
      - revision
      - created_at
      - tags
      - path
      - mtime
    Sorted newest → oldest.
    """
    entries: List[Dict[str, Any]] = []
    for path in _find_holo_paths_for_container(container_id):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[HOLO] Failed to read holo index entry {path}: {e}")
            continue

        holo_id = data.get("holo_id")
        cid = data.get("container_id", container_id)
        timefold = data.get("timefold") or {}
        version = data.get("version") or {}
        origin = data.get("origin") or {}
        indexing = data.get("indexing") or {}

        entries.append(
            {
                "holo_id": holo_id,
                "container_id": cid,
                "tick": timefold.get("tick"),
                "revision": version.get("revision"),
                "created_at": origin.get("created_at"),
                "tags": indexing.get("tags", []),
                "path": str(path),
                "mtime": path.stat().st_mtime,
            }
        )

    # Already sorted by _find_holo_paths_for_container (newest first)
    return entries


def load_holo_for_container_at(
    container_id: str,
    tick: int,
    revision: int = 1,
) -> Optional[HoloIR]:
    """
    Load a specific holo snapshot for a container by (tick, revision).

    Relies on the filename pattern produced in export_holo_from_container:
      "holo:container/<cid>/t=<tick>/v<rev>" →
      "holo_container_<cid>_t=<tick>_v<rev>.holo.json"
    """
    root: Path = HOLO_ROOT

    # Prefer nested dir if present
    nested_dir = root / container_id
    if nested_dir.exists():
        pattern = nested_dir / f"*t={tick}_v{revision}.holo.json"
    else:
        # Fall back to flat/legacy root
        pattern = root / f"*{container_id}*t={tick}_v{revision}.holo.json"

    matches = [Path(p) for p in glob.glob(str(pattern))]
    if not matches:
        return None

    # If multiple, pick the newest
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    path = matches[0]

    try:
        return load_holo(str(path))
    except Exception as e:
        print(
            f"[HOLO] load_holo_for_container_at failed for {container_id} t={tick} v={revision}: {e}"
        )
        return None

def export_holo_from_kg_pack(
    *,
    container_id: str,
    kg_pack: Dict[str, Any],
    view_ctx: Dict[str, Any],
    revision: int = 1,
) -> HoloIR:
    """
    Variant of export_holo_from_container which takes a KG pack directly.
    Used by the HST pipeline (code → HST → KG pack → .holo).
    """
    tick = int(view_ctx.get("tick", 0))
    holo_id = f"holo:container/{container_id}/t={tick}/v{revision}"

    nodes = kg_pack.get("nodes", [])
    links = kg_pack.get("links", [])

    metrics = view_ctx.get("metrics") or {
        "coherence": 1.0,
        "drift": 0.0,
        "tick": tick,
    }

    holo = HoloIR(
        holo_id=holo_id,
        container_id=container_id,
        name=kg_pack.get("meta", {}).get("name"),
        symbol=kg_pack.get("meta", {}).get("symbol"),
        kind=view_ctx.get("kind", "memory"),
        origin={
            "source": "hst_from_code",
            "language": kg_pack.get("meta", {}).get("language"),
        },
        version={
            "schema": 1,
            "revision": revision,
        },
        ghx={
            "nodes": nodes,
            "edges": links,
            "layout": kg_pack.get("meta", {}).get("layout"),
            "ghx_mode": "hologram",
            "entangled_links": kg_pack.get("meta", {}).get("entangled_links", []),
        },
        field={
            "psi_kappa_T": {
                "frame": view_ctx.get("frame", "original"),
                "state_vector": view_ctx.get("psi_state") or {},
            },
            "metrics": metrics,
        },
        beams=[],
        multiverse_frame=view_ctx.get("frame", "original"),
        views=view_ctx.get("views", {}),
        indexing={
            "tags": view_ctx.get("tags", []),
        },
        timefold={
            "tick": tick,
            "t_label": view_ctx.get("t_label"),
        },
        references={
            "container_id": container_id,
        },
    )

    # persist .holo JSON
    out_dir = HOLO_ROOT / container_id
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{holo_id.replace(':', '_').replace('/', '_')}.holo.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(holo.__dict__, f, indent=2)

    return holo


def save_holo_from_dict(holo_dict: Dict[str, Any]) -> HoloIR:
    """
    Used by /api/holo/import and motif pipeline.
    Normalises an incoming dict into HoloIR, assigns defaults, persists it.
    """
    holo_id = holo_dict.get("holo_id")
    container_id = holo_dict.get("container_id")

    if not holo_id or not container_id:
        raise ValueError("holo_id and container_id are required to import a HoloIR")

    holo = HoloIR(**holo_dict)

    out_dir = HOLO_ROOT / container_id
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{holo_id.replace(':', '_').replace('/', '_')}.holo.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(holo.__dict__, f, indent=2)

    return holo