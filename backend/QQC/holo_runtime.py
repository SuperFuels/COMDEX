# backend/QQC/holo_runtime.py
from __future__ import annotations

from typing import Dict, Any, Optional

try:
    # Symatics Lightwave WaveCapsule API
    from backend.modules.symatics_lightwave.wave_capsule import (
        run_symatics_wavecapsule,
    )
except Exception:  # pragma: no cover
    run_symatics_wavecapsule = None  # type: ignore


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
        },
    }
    return spec


def _interpret_program_frames(
    holo: Dict[str, Any],
    input_ctx: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Tiny demo interpreter for program_frames.

    Supported roles:
      • "input":   load a value from input_ctx (config.from, default "x")
      • "const":   set current value to a constant (config.value)
      • "mul":     multiply current value by factor (config.factor)
      • "add":     add a constant (config.value)
      • "sub":     subtract a constant (config.value)
      • "div":     divide by a constant (config.value)
      • "output":  write current value into state[config.to] (default "result")

    Frames are run in ascending order of `order` (or list order if missing).
    Result is the final state dict (input_ctx + any new vars, e.g. "y").
    """
    extra = holo.get("extra") or {}
    frames = extra.get("program_frames") or []
    if not isinstance(frames, list) or not frames:
        return {}

    ordered = sorted(
        [f for f in frames if isinstance(f, dict)],
        key=lambda f: f.get("order", 0),
    )

    state: Dict[str, Any] = dict(input_ctx)
    val: Any = None

    for f in ordered:
        role = f.get("role")
        cfg = f.get("config") or {}

        if role == "input":
            src_key = cfg.get("from", "x")
            val = state.get(src_key)

        elif role == "const":
            val = cfg.get("value")

        elif role == "mul" and val is not None:
            try:
                val = val * cfg.get("factor", 1)
            except Exception:
                pass

        elif role == "add" and val is not None:
            try:
                val = val + cfg.get("value", 0)
            except Exception:
                pass

        elif role == "sub" and val is not None:
            try:
                val = val - cfg.get("value", 0)
            except Exception:
                pass

        elif role == "div" and val is not None:
            try:
                denom = cfg.get("value", 1)
                if denom not in (0, 0.0):
                    val = val / denom
            except Exception:
                pass

        elif role == "output" and val is not None:
            dst_key = cfg.get("to", "result")
            state[dst_key] = val

    return state


def execute_holo_program(
    holo: Dict[str, Any],
    input_ctx: Dict[str, Any],
    mode: str = "qqc",
) -> Dict[str, Any]:
    """
    Run a HoloIR object through the Symatics/SLE pipeline AND
    evaluate a tiny arithmetic 'program' encoded in extra.program_frames.

    Returns:
      {
        "output": {
          "sle_status": ...,
          "echo_input_ctx": {...},
          "program_output": {...},  # only if program_frames existed
        },
        "metrics": {...},
        "sle_status": "...",
        "sle_spec": {...},
      }
    """
    # Build the WaveCapsule spec from the holo + input ctx
    spec = _build_capsule_spec_from_holo(holo, input_ctx, mode=mode)

    # --- Call Symatics/SLE + BeamRuntime (WaveCapsule) ----------------------
    sle_result: Dict[str, Any] = {}
    if run_symatics_wavecapsule is not None:
        try:
            sle_result = run_symatics_wavecapsule(spec) or {}
        except Exception as e:
            # Keep DevTools alive even if SLE is misconfigured.
            print(f"[HOLO-CPU] run_symatics_wavecapsule failed: {e!r}")
            sle_result = {
                "status": "sle_error",
                "error": str(e),
                "mode": mode,
            }
    else:
        sle_result = {
            "status": "no_wavecapsule",
            "mode": mode,
        }

    coherence = sle_result.get("coherence")
    collapse_time_ms = sle_result.get("collapse_time_ms")
    opcode = sle_result.get("opcode") or spec.get("opcode")
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

    # --- Tiny demo interpreter over program_frames -------------------------
    program_state = _interpret_program_frames(holo, input_ctx)

    output: Dict[str, Any] = {
        "sle_status": status,
        "echo_input_ctx": input_ctx,
    }
    if program_state:
        # e.g. { "x": 10, "y": 23 }
        output["program_output"] = program_state

    # --- Build a tiny GHX graph for the program frames -------------
    ghx_payload: Optional[Dict[str, Any]] = None
    try:
        extra = (holo or {}).get("extra") or {}
        frames = extra.get("program_frames") or []
        if frames:
            nodes = []
            for idx, f in enumerate(frames):
                fid = f.get("id") or f"f_{idx}"
                nodes.append(
                    {
                        "id": fid,
                        "label": f.get("label") or fid,
                        "kind": f.get("role") or "frame",
                    }
                )

            ghx_src = (holo or {}).get("ghx") or {}
            edges = ghx_src.get("edges") or []

            # Fallback: linear chain if no edges were defined
            if not edges and len(nodes) > 1:
                edges = [
                    {
                        "id": f"e_{i}",
                        "source": nodes[i]["id"],
                        "target": nodes[i + 1]["id"],
                        "kind": "flow",
                    }
                    for i in range(len(nodes) - 1)
                ]

            ghx_payload = {
                "ghx_version": "1.0",
                "origin": "holo_program",
                "container_id": (
                    holo.get("container_id")
                    if isinstance(holo, dict)
                    else input_ctx.get("container_id", "devtools")
                ),
                "nodes": nodes,
                "edges": edges,
                "metadata": {
                    "holo_id": (holo or {}).get("holo_id"),
                    "tick": (holo or {}).get("timefold", {}).get("tick"),
                    "program_output": program_state,
                },
            }
    except Exception as e:
        print(f"[HOLO-CPU] failed to derive GHX from program_frames: {e!r}")
        ghx_payload = None

    result: Dict[str, Any] = {
        "output": output,
        "metrics": metrics,
        "sle_status": status,
        "sle_spec": spec,
    }
    if ghx_payload is not None:
        result["ghx"] = ghx_payload

    return result