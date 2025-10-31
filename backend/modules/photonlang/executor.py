# ============================================================
# Photon Runtime Executor (v0.2)
# ------------------------------------------------------------
# Executes photon capsules:
#  - async runtime
#  - Symatics ↔ Photon bridge
#  - collapse + pulse validity
#  - SQI telemetry trace
# ============================================================

from __future__ import annotations
import asyncio
import time
from typing import Any, Dict

from backend.modules.photonlang.binary_mode import to_binary
from backend.modules.photonlang.telemetry import emit_sqi_event
from backend.modules.symatics_lightwave.symatics_dispatcher import run_symatics_wavecapsule

# ------------------------------------------------------------
# Capsule Normalization
# ------------------------------------------------------------

def _normalize_capsule(c: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": c.get("id") or f"cap-{id(c)}",
        "opcode": c.get("opcode") or c.get("op"),
        "args": c.get("args", []),
        "engine": c.get("engine", "lightwave"),
        "meta": c.get("meta", {}),
    }


# ------------------------------------------------------------
# Core Execution
# ------------------------------------------------------------

async def execute_capsule(cap: Dict[str, Any]) -> Dict[str, Any]:
    cap = _normalize_capsule(cap)
    cid = cap["id"]
    opcode = cap["opcode"]

    start_time = time.time()

    emit_sqi_event("capsule_start", {
        "id": cid,
        "op": opcode
    })

    try:
        # --- dispatch to Symatics/Lightwave hybrid engine ---
        result = run_symatics_wavecapsule(cap)

        # --- collapse glyph if present ---
        glyph = result.get("operator") or cap.get("opcode")
        bits = to_binary(glyph)
        pulse_ok = bool(bits)

        # annotate
        result.update({
            "capsule_id": cid,
            "pulse_ok": pulse_ok,
            "binary": bits,
        })

        status = "ok"

    except Exception as e:
        result = {"error": str(e), "capsule_id": cid}
        status = "error"

    elapsed = round(time.time() - start_time, 6)

    emit_sqi_event("capsule_done", {
        "id": cid,
        "op": opcode,
        "status": status,
        "elapsed": elapsed
    })

    return result


# ------------------------------------------------------------
# Synchronous wrapper
# ------------------------------------------------------------

def execute_capsule_sync(cap: Dict[str, Any]) -> Dict[str, Any]:
    return asyncio.get_event_loop().run_until_complete(execute_capsule(cap))


# ------------------------------------------------------------
# Parallel capsule batch runner (optional direct use)
# ------------------------------------------------------------

async def execute_parallel_capsules(capsules, max_parallel=4):
    """
    Convenience helper: submit list, run until queue emptied.
    (Thin wrapper around ParallelCapsuleExecutor)
    """
    from backend.modules.photonlang.parallel_capsules import ParallelCapsuleExecutor

    ex = ParallelCapsuleExecutor(max_parallel=max_parallel)
    for c in capsules:
        ex.submit(c)

    task = asyncio.create_task(ex.run())
    await asyncio.sleep(0.001)  # allow loop to start
    return ex, task