# /workspaces/COMDEX/backend/QQC/holo_runtime.py
from __future__ import annotations

from typing import Any, Dict
from datetime import datetime, timezone

from backend.QQC.wave_capsule import run_symatics_wavecapsule


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_capsule_spec_from_holo(
    holo: Dict[str, Any],
    input_ctx: Dict[str, Any],
    mode: str = "qqc",
) -> Dict[str, Any]:
    """
    Minimal bridge from HoloIR → Symatics/SLE spec.

    This does NOT try to interpret the holo graph as a full program yet;
    it just feeds the hologram + input_ctx into the Symatics engine so we
    get real coherence + beam events via BeamRuntime.
    """
    container_id = (
        holo.get("container_id")
        or input_ctx.get("container_id")
        or "holo::unknown"
    )
    timefold = holo.get("timefold") or {}
    tick = timefold.get("tick", 0)
    holo_id = holo.get("holo_id") or f"holo:container/{container_id}/t={tick}"

    ghx = holo.get("ghx") or {}
    nodes = ghx.get("nodes") or []
    edges = ghx.get("edges") or ghx.get("links") or []

    extra = holo.get("extra") or {}
    program_frames = extra.get("program_frames") or []

    # For now this is a single Symatics op that carries the holo context
    # as arguments. Later we can interpret frames/edges as a true program.
    spec: Dict[str, Any] = {
        "capsule_id": f"holo_exec::{holo_id}",
        "container_id": container_id,
        "engine": "symatics_lightwave",
        # Use superposition as a generic "run" op for now.
        "opcode": "⊕",
        "args": [
            {
                "kind": "holo_program",
                "holo_id": holo_id,
                "tick": tick,
                "nodes": nodes,
                "edges": edges,
                "program_frames": program_frames,
                "input_ctx": input_ctx,
                "mode": mode,
            }
        ],
        "params": {
            "mode": mode,
            "ghx_node_count": len(nodes),
            "ghx_edge_count": len(edges),
            "invoked_at": _utc_now_iso(),
        },
    }
    return spec


def execute_holo_program(
    holo: Dict[str, Any],
    input_ctx: Dict[str, Any],
    mode: str = "qqc",
) -> Dict[str, Any]:
    """
    Run a HoloIR object through the Symatics/SLE pipeline.

    Returns a small dict that run_holo_snapshot can merge into its
    response: { output, metrics, sle_status, sle_spec }.

    Side effects:
      • Uses run_symatics_wavecapsule(...) which internally:
        - builds a WaveCapsule,
        - calls BeamRuntime.execute_capsule(...),
        - emits BeamEvent objects on beam_event_bus.
      • QQCQFCAdapter is already subscribed to beam_event_bus, so QFC
        overlays will see these beams.
    """
    spec = _build_capsule_spec_from_holo(holo, input_ctx, mode=mode)

    try:
        # This calls SymaticsDispatcher + BeamRuntime under the hood.
        sle_result: Dict[str, Any] = run_symatics_wavecapsule(spec) or {}
    except Exception as e:
        # Don’t break DevTools if SLE is misconfigured – surface an error
        # payload but keep the contract.
        print(f"[HOLO-RUNTIME] run_symatics_wavecapsule failed: {e!r}")
        return {
            "output": {
                "sle_status": "error",
                "error": str(e),
                "echo_input_ctx": input_ctx,
            },
            "metrics": {
                "sle_status": "error",
            },
            "sle_status": "error",
            "sle_spec": spec,
        }

    # BeamRuntime.execute_capsule typically returns at least:
    #   { "opcode", "mode", "coherence", "collapse_time_ms", "status", ... }
    coherence = sle_result.get("coherence")
    collapse_time_ms = sle_result.get("collapse_time_ms")
    opcode = sle_result.get("opcode")
    status = sle_result.get("status") or "executed"

    metrics: Dict[str, Any] = {
        "sle_opcode": opcode,
        "sle_mode": sle_result.get("mode", mode),
        "sle_status": status,
    }
    if coherence is not None:
        metrics["sle_coherence"] = coherence
    if collapse_time_ms is not None:
        metrics["sle_collapse_time_ms"] = collapse_time_ms

    return {
        "output": {
            # For now we don't try to decode a rich payload from SLE;
            # we just echo the input ctx alongside the SLE status.
            "sle_status": status,
            "echo_input_ctx": input_ctx,
        },
        "metrics": metrics,
        "sle_status": status,
        "sle_spec": spec,
    }


# --------------------------------------------------------------------
# Backwards-compatible entrypoint for run_holo_snapshot
# --------------------------------------------------------------------
async def run_holo(
    holo: Dict[str, Any],
    input_ctx: Dict[str, Any],
    mode: str = "qqc",
) -> Dict[str, Any]:
    """
    Async wrapper kept for compatibility with existing calls:

        engine_result = await run_holo(holo, input_ctx, mode)

    Internally this just calls execute_holo_program(...).
    """
    return execute_holo_program(holo, input_ctx, mode=mode)