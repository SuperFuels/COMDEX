# File: backend/modules/gip/gip_executor.py

import logging
from typing import Dict, Any, Optional
import asyncio

from ..glyphos.glyph_executor import execute_glyph_logic
from ..glyphos.glyph_logic import parse_glyph_packet
from ..codex.codex_context_adapter import CodexContextAdapter
from ..codex.codex_metrics import record_execution_metrics
from ..hexcore.memory_engine import store_memory
from ..codex.codex_trace import CodexTrace
from ..glyphos.codexlang_translator import run_codexlang_string
from ..dimensions.container_linker import create_bidirectional_link
from .gip_broadcast import broadcast_to_codex_and_aion

logger = logging.getLogger(__name__)

def execute_gip_packet(packet: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes a GIP packet symbolically based on its type and embedded glyph logic.
    Returns a result dictionary with status and optional execution output.
    """
    try:
        packet_type = packet.get("type")
        glyphs = packet.get("glyphs", [])
        metadata = packet.get("meta", {})
        trace_id = metadata.get("trace_id")

        logger.info(f"[GIP] Executing packet type: {packet_type} with {len(glyphs)} glyphs")

        if trace_id:
            CodexTrace.log_event("gip_packet_received", {
                "trace_id": trace_id,
                "type": packet_type,
                "glyphs": glyphs
            })

        if packet_type == "symbolic_thought":
            output = []
            for glyph_data in glyphs:
                logic_tree = parse_glyph_packet(glyph_data)
                exec_result = execute_glyph_logic(logic_tree, context=context)

                store_memory(exec_result.get("memory"))
                record_execution_metrics("gip_thought", exec_result)

                if trace_id:
                    CodexTrace.log_event("glyph_executed", {
                        "trace_id": trace_id,
                        "glyph": glyph_data.get("glyph"),
                        "result": exec_result
                    })

                output.append(exec_result)

            asyncio.create_task(broadcast_to_codex_and_aion(packet))
            return {"status": "ok", "executed": output, "meta": metadata}

        elif packet_type == "trigger" and "trigger_glyph" in metadata:
            glyph = metadata["trigger_glyph"]
            logic_tree = parse_glyph_packet({"glyph": glyph})
            result = execute_glyph_logic(logic_tree, context=context)

            store_memory(result.get("memory"))
            record_execution_metrics("gip_trigger", result)

            if trace_id:
                CodexTrace.log_event("trigger_executed", {
                    "trace_id": trace_id,
                    "glyph": glyph,
                    "result": result
                })

            asyncio.create_task(broadcast_to_codex_and_aion(packet))
            return {"status": "ok", "result": result, "meta": metadata}

        elif packet_type == "link" and "containers" in metadata:
            links = []
            for pair in metadata["containers"]:
                link = create_bidirectional_link(pair[0], pair[1])
                links.append(link)

            if trace_id:
                CodexTrace.log_event("link_created", {
                    "trace_id": trace_id,
                    "links": links
                })

            asyncio.create_task(broadcast_to_codex_and_aion(packet))
            return {"status": "ok", "linked": links, "meta": metadata}

        elif packet_type == "codexlang" and "code" in metadata:
            code = metadata["code"]
            result = run_codexlang_string(code)

            if trace_id:
                CodexTrace.log_event("codexlang_executed", {
                    "trace_id": trace_id,
                    "code": code,
                    "result": result
                })

            store_memory(result.get("memory"))
            record_execution_metrics("gip_codexlang", result)

            asyncio.create_task(broadcast_to_codex_and_aion(packet))
            return {"status": "ok", "result": result, "meta": metadata}

        else:
            logger.warning(f"[GIP] Unknown packet type or invalid structure: {packet_type}")
            return {"status": "error", "error": "Invalid packet type or data"}

    except Exception as e:
        logger.exception("[GIP] Execution failed")
        return {"status": "error", "error": str(e)}