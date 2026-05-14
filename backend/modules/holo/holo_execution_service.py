# backend/modules/holo/holo_execution_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.QQC.holo_runtime import execute_holo_program
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.dna_chain.container_index_writer import add_to_index
from backend.modules.glyphwave.emit_beam import emit_qwave_beam as emit_symbolic_beam

# Optional: live QWave beam collector – not strictly used yet, but kept for future wiring
try:
    from backend.modules.glyphwave.qwave.qwave_writer import (
        collect_qwave_beams as _collect_qwave_beams,
    )
except Exception:  # pragma: no cover
    _collect_qwave_beams = None

# Optional: .holo persistence – we fail soft if it's missing
try:
    from backend.modules.holo.holo_service import (
        save_holo_from_dict as _save_holo_from_dict,
    )
except Exception:  # pragma: no cover
    _save_holo_from_dict = None


@dataclass
class RunHoloResult:
    """
    Structured result for run_holo_snapshot, but we still return dicts
    outward (FastAPI / JSON). This just keeps the shape explicit.
    """
    status: str
    message: Optional[str]
    container_id: str
    holo_id: Optional[str]
    tick: Optional[int]
    beams: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    output: Dict[str, Any]
    updated_holo: Optional[Dict[str, Any]]
    # NEW: GHX packet for Field canvas
    ghx: Optional[Dict[str, Any]] = None
    # NEW: persistence info (U4D)
    new_holo_id: Optional[str] = None
    new_revision: Optional[int] = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_container_and_tick(
    holo: Dict[str, Any],
    input_ctx: Optional[Dict[str, Any]],
) -> tuple[str, Optional[int]]:
    """
    Pull container_id + tick out of the holo / input_ctx in a tolerant way.
    """
    container_id = str(holo.get("container_id") or "unknown")

    tick: Optional[int] = None
    # Prefer timefold.tick if present
    tf = holo.get("timefold") or {}
    if "tick" in tf:
        try:
            tick = int(tf.get("tick"))
        except Exception:
            tick = None

    # Fallback: input_ctx.tick
    if tick is None and input_ctx is not None:
        try:
            if "tick" in input_ctx:
                tick = int(input_ctx.get("tick"))
        except Exception:
            tick = None

    return container_id, tick


def emit_beams_from_holo(holo: Dict[str, Any], mode: str = "qqc") -> List[Dict[str, Any]]:
    """
    VERY MINIMAL placeholder:

    Look at holo.ghx.edges (or links) and synthesise QWave-like beams so the
    DevTools / QFC field can visualise *something* when you press ▶ Run .holo.

    This does NOT hit the real QWave / BeamRuntime stack yet – it’s just a
    structural bridge: GHX edge → beam dict.
    """
    ghx = holo.get("ghx") or {}
    edges = ghx.get("edges") or ghx.get("links") or []
    if not isinstance(edges, list):
        return []

    beams: List[Dict[str, Any]] = []

    for idx, raw in enumerate(edges):
        e = raw or {}

        # Tolerate all the usual GHX endpoint shapes
        src_id = (
            e.get("source")
            or e.get("src")
            or e.get("from")
            or e.get("src_id")
            or None
        )
        dst_id = (
            e.get("target")
            or e.get("dst")
            or e.get("to")
            or e.get("dst_id")
            or None
        )

        if not src_id or not dst_id:
            continue

        beam_id = e.get("id") or f"holo-beam-{idx}"

        beams.append(
            {
                "id": beam_id,
                "source": src_id,
                "target": dst_id,
                "carrier_type": "HOLO_SYNTH",
                "modulation": mode or "qqc",
                "coherence": 1.0,
                "collapse_state": "original",
                "entangled_path": [src_id, dst_id],
                "mutation_trace": [],
                "metadata": {
                    "from_holo": True,
                    "edge_kind": e.get("kind"),
                },
            }
        )

    return beams


def _collect_beams_for_container(container_id: str) -> List[Dict[str, Any]]:
    """
    Optional live beam collection via qwave_writer.

    Right now we don't rely on this for the ▶ Run .holo UX, but keep it
    around so we can blend real beams in later.
    """
    if not _collect_qwave_beams:
        return []

    try:
        raw_beams = _collect_qwave_beams(container_id) or []
    except Exception as e:
        print(f"[HOLO-RUN] collect_qwave_beams failed for {container_id}: {e}")
        return []

    shaped: List[Dict[str, Any]] = []
    for b in raw_beams:
        shaped.append(
            {
                "id": b.get("id"),
                "source": b.get("source") or b.get("source_id"),
                "target": b.get("target") or b.get("target_id"),
                "carrier_type": b.get("carrier_type", "SIMULATED"),
                "modulation": b.get("modulation") or b.get("modulation_strategy", "SimPhase"),
                "coherence": b.get("coherence", 1.0),
                "entangled_path": b.get("entangled_path", []),
                "mutation_trace": b.get("mutation_trace", []),
                "collapse_state": b.get("collapse_state", "original"),
                "metadata": b.get("metadata", {}),
            }
        )
    return shaped


async def run_holo_snapshot(
    holo: Dict[str, Any],
    input_ctx: Optional[Dict[str, Any]] = None,
    mode: str = "qqc",
) -> Dict[str, Any]:
    """
    DevTools “▶ Run .holo” entrypoint.

    Now:
      • calls execute_holo_program(...) for real SLE/BeamRuntime metrics
      • bumps revision + saves a fresh .holo revision when possible
      • writes a holo_run glyph into KG for analytics
    """
    input_ctx = input_ctx or {}
    container_id, tick = _derive_container_and_tick(holo, input_ctx)

    try:
        # --- 1) Clone + bump revision / run metadata -------------------------
        updated = dict(holo)
        extra = dict(updated.get("extra") or {})
        run_count = int(extra.get("run_count", 0)) + 1

        extra.update(
            {
                "run_count": run_count,
                "last_run_at": _utc_now_iso(),
                "last_run_mode": mode,
            }
        )
        updated["extra"] = extra

        version = dict(updated.get("version") or {})
        prev_revision = int(version.get("revision") or 0)
        new_revision = prev_revision + 1
        version["revision"] = new_revision
        updated["version"] = version

        # --- 2) Execute via Symatics/SLE pipeline ----------------------------
        sle_result: Dict[str, Any] = {}
        try:
            sle_result = execute_holo_program(updated, input_ctx, mode=mode)
        except Exception as e:
            print(f"[HOLO-RUN] SLE execution failed (will continue): {e!r}")

        sle_output = sle_result.get("output") or {}
        sle_metrics = sle_result.get("metrics") or {}

        # --- 3) Beams + tiny GHX packet for DevTools/QFC --------------------
        # 3a) Synthetic beams from holo.ghx edges (for visuals)
        beams: List[Dict[str, Any]] = emit_beams_from_holo(updated, mode=mode)

        # 3a.1) Optional: append live QWave beams if qwave_writer is present
        live_beams = _collect_beams_for_container(container_id)
        if live_beams:
            beams.extend(live_beams)

        num_beams = len(beams)

        # 3b) Build a tiny GHX packet from program_frames (for the field cards)
        ghx_packet: Optional[Dict[str, Any]] = None
        extra_frames = (updated.get("extra") or {}).get("program_frames") or []
        if isinstance(extra_frames, list) and extra_frames:
            nodes: List[Dict[str, Any]] = []
            edge_list: List[Dict[str, Any]] = []

            for f in extra_frames:
                if not isinstance(f, dict):
                    continue
                fid = f.get("id") or f.get("label") or f"frame_{len(nodes)}"
                nodes.append(
                    {
                        "id": fid,
                        "label": f.get("label") or fid,
                        "type": "holo_node",
                        "tags": [],
                        "meta": {},
                        "data": {"from": "holo"},
                    }
                )

            updated_ghx = updated.get("ghx") or {}
            existing_edges = updated_ghx.get("edges") or []

            if isinstance(existing_edges, list) and existing_edges:
                for e in existing_edges:
                    if not isinstance(e, dict):
                        continue
                    src = e.get("source") or e.get("src")
                    dst = e.get("target") or e.get("dst")
                    if not src or not dst:
                        continue
                    edge_list.append(
                        {
                            "id": e.get("id") or f"e{len(edge_list)+1}",
                            "src": src,
                            "dst": dst,
                            "source": src,
                            "target": dst,
                            "tags": e.get("tags") or [],
                            "meta": e.get("meta") or {},
                            "data": {"from": "holo"},
                        }
                    )
            else:
                for i in range(len(extra_frames) - 1):
                    src = extra_frames[i].get("id") or f"frame_{i}"
                    dst = extra_frames[i + 1].get("id") or f"frame_{i+1}"
                    edge_list.append(
                        {
                            "id": f"e{i+1}",
                            "src": src,
                            "dst": dst,
                            "source": src,
                            "target": dst,
                            "tags": [],
                            "meta": {},
                            "data": {"from": "holo"},
                        }
                    )

            ghx_packet = {
                "ghx_version": "1.0",
                "origin": updated.get("holo_id")
                or holo.get("holo_id")
                or "holo_program",
                "container_id": updated.get("container_id") or container_id,
                "nodes": nodes,
                "edges": edge_list,
                "metadata": {
                    "holo_id": updated.get("holo_id") or holo.get("holo_id"),
                    "kind": "memory",
                    "timefold": {
                        "t_label": None,
                        "tick": (updated.get("timefold") or {}).get(
                            "tick", tick or 0
                        ),
                    },
                },
            }

        # --- 3c) Mirror synthetic beams into the real QWave pipeline --------
        # This uses emit_qwave_beam from backend.modules.glyphwave.emit_beam,
        # which builds a WaveState, validates via SoulLaw, and appends the
        # beam to the container for later exports / analytics.
        try:
            for b in beams:
                src_frame = b.get("source_frame")
                dst_frame = b.get("target_frame")
                if not src_frame or not dst_frame:
                    continue

                emit_symbolic_beam(
                    glyph_id=str(src_frame),            # stand-in glyph id
                    result=None,
                    source="holo_run",
                    context={
                        "container_id": container_id,
                        "tick": tick or 0,
                    },
                    state="predicted",
                    metadata={
                        "target": str(dst_frame),
                        "holo_id": updated.get("holo_id") or holo.get("holo_id"),
                        "beam_kind": b.get("kind"),
                    },
                )
        except Exception as e:
            print(f"[HOLO-RUN] emit_qwave_beam failed: {e}")

        # --- 4) Merge metrics ------------------------------------------------
        metrics: Dict[str, Any] = {
            "num_beams": num_beams,
            "run_count": run_count,
            "tick": tick,
            "mode": mode,
        }
        metrics.update(sle_metrics)

        # --- 5) Persist updated_holo as a new revision, if saver is available
        updated_holo: Optional[Dict[str, Any]] = None
        new_holo_id: Optional[str] = None

        if _save_holo_from_dict is not None:
            try:
                saved = _save_holo_from_dict(updated)  # type: ignore[call-arg]

                if hasattr(saved, "__dict__"):
                    saved_dict = dict(saved.__dict__)
                elif isinstance(saved, dict):
                    saved_dict = saved
                else:
                    saved_dict = updated

                updated_holo = saved_dict
                new_holo_id = (
                    saved_dict.get("holo_id")
                    or getattr(saved, "holo_id", None)
                    or updated.get("holo_id")
                )

                # Ensure we expose a revision number
                saved_version = saved_dict.get("version") or {}
                if isinstance(saved_version, dict):
                    new_revision = int(saved_version.get("revision") or new_revision)
            except Exception as e:
                print(f"[HOLO-RUN] save_holo_from_dict failed: {e}")
                updated_holo = updated
                new_holo_id = updated.get("holo_id")
        else:
            updated_holo = updated
            new_holo_id = updated.get("holo_id")

        # --- 6) Push run into KG as an analytics glyph ----------------------
        try:
            writer = get_kg_writer()
            writer.inject_glyph(
                content=f"HoloRun:{new_holo_id or (holo.get('holo_id') or container_id)}",
                glyph_type="holo_run",
                metadata={
                    "container_id": container_id,
                    "holo_id": new_holo_id or holo.get("holo_id"),
                    "tick": tick,
                    "mode": mode,
                    "metrics": metrics,
                },
                plugin="HoloCPU",
            )
        except Exception as e:
            print(f"[HOLO-RUN] KG holo_run glyph inject failed: {e}")

        # --- 7) Index the run as a holo revision (searchable history) -------
        try:
            add_to_index(
                "knowledge_index.holo",
                {
                    "id": new_holo_id or holo.get("holo_id"),
                    "type": "holo_run",
                    "timestamp": _utc_now_iso(),
                    "content": {
                        "container_id": container_id,
                        "tick": tick,
                        "revision": new_revision,
                    },
                    "metadata": {
                        "metrics": metrics,
                        "mode": mode,
                    },
                },
            )
        except Exception as e:
            print(f"[HOLO-RUN] add_to_index(holo) failed: {e}")

        # --- 8) Final payload back to DevTools -------------------------------
        output = sle_output or {"echo_input_ctx": input_ctx}

        result = RunHoloResult(
            status="ok",
            message=None,
            container_id=container_id,
            holo_id=new_holo_id or holo.get("holo_id"),
            tick=tick,
            beams=beams,
            metrics=metrics,
            output=output,
            updated_holo=updated_holo,
            new_holo_id=new_holo_id,
            new_revision=new_revision,
            ghx=ghx_packet,
        )
        return result.__dict__

    except Exception as e:
        print(f"[HOLO-RUN] unexpected error while running holo: {e}")
        error_result = RunHoloResult(
            status="error",
            message=f"run_holo_snapshot failed: {e}",
            container_id=container_id,
            holo_id=holo.get("holo_id"),
            tick=tick,
            beams=[],
            metrics={},
            output={},
            updated_holo=None,
            new_holo_id=None,
            new_revision=None,
        )
        return error_result.__dict__