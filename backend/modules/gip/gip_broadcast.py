# File: backend/modules/gip/gip_broadcast.py

import asyncio
import logging
from typing import Dict, Any

from ..codex.codex_context_adapter import forward_packet_to_codex
from ..aion.aion_bridge import process_symbolic_input

logger = logging.getLogger(__name__)

async def broadcast_to_codex_and_aion(packet: Dict[str, Any]):
    try:
        logger.info("[GIP] Broadcasting packet to Codex and AION")
        codex_future = asyncio.create_task(forward_packet_to_codex(packet))
        aion_future = asyncio.create_task(process_symbolic_input(packet))

        await asyncio.gather(codex_future, aion_future)
    except Exception as e:
        logger.error(f"[GIP] Broadcast failed: {e}")