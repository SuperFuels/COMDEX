# backend/modules/gip/gip_broadcast.py
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Callable, Awaitable

# WaveCapsule executor (present in your tree)
from backend.modules.symatics_lightwave.wave_capsule import run_symatics_wavecapsule

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Optional fan-out targets: import if available, else no-ops
# ------------------------------------------------------------
async def _noop_forward_packet_to_codex(packet: Dict[str, Any]) -> None:
    logger.debug("[GIP] forward_packet_to_codex not present; noop.")

async def _noop_process_symbolic_input(packet: Dict[str, Any]) -> None:
    logger.debug("[GIP] process_symbolic_input not present; noop.")

_forward_packet_to_codex: Callable[[Dict[str, Any]], Awaitable[None]] = _noop_forward_packet_to_codex
_process_symbolic_input: Callable[[Dict[str, Any]], Awaitable[None]] = _noop_process_symbolic_input

try:
    # If you later add these, the real ones will be used automatically.
    from backend.modules.gip.codex_forward import forward_packet_to_codex as _forward_packet_to_codex  # type: ignore
except Exception:
    pass

try:
    from backend.modules.gip.symbolic_input import process_symbolic_input as _process_symbolic_input  # type: ignore
except Exception:
    pass

# ------------------------------------------------------------
# Helper: create task safely (works even if called very early)
# ------------------------------------------------------------
def _safe_create_task(coro: Awaitable[Any]) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # No running loop (very early boot) — run in a background thread
        asyncio.run(coro)

# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------
async def broadcast_to_codex_and_aion(packet: Dict[str, Any]) -> None:
    """
    Fan out a GIP packet to Codex + AION, with an opportunistic WaveCapsule
    execution when op/symbol == 'wave'.
    """
    try:
        logger.info("[GIP] Broadcasting packet to Codex and AION")

        # 0) Opportunistic WaveCapsule execute for 'wave' ops
        try:
            pl = packet.get("payload") or {}
            frame = pl.get("frame") if isinstance(pl, dict) and "frame" in pl else pl
            body = frame.get("body") if isinstance(frame, dict) else {}
            op = (body.get("op") or "").lower()
            sym = (packet.get("symbol") or "").lower()

            if op == "wave" or sym == "wave":
                text = (
                    ((body.get("payload") or {}).get("text"))
                    or ((packet.get("meta") or {}).get("text"))
                    or ""
                )
                spec = {
                    "opcode": "WAVE",
                    "args": [text],
                    "container_id": packet.get("recipient") or "ucs_hub",
                }
                # run the (potentially blocking) wave capsule off the event loop
                _safe_create_task(asyncio.to_thread(run_symatics_wavecapsule, spec))
        except Exception as e:
            logger.debug(f"[GIP] WaveCapsule dispatch skipped: {e}")

        # 1) Fan-out (real implementations if present, else no-ops)
        codex_future = asyncio.create_task(_forward_packet_to_codex(packet))
        aion_future = asyncio.create_task(_process_symbolic_input(packet))
        await asyncio.gather(codex_future, aion_future)

    except Exception as e:
        logger.error(f"[GIP] Broadcast failed: {e}")