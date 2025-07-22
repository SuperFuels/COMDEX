# File: backend/modules/gip/gip_executor.py

from ..glyphos.glyph_executor import execute_glyph_logic
from ..glyphos.glyph_logic import parse_glyph_packet
from ..codex/codex_context_adapter import CodexContextAdapter
from ..codex/codex_metrics import record_execution_metrics
from ..hexcore.memory_engine import store_memory

import logging

logger = logging.getLogger(__name__)


def execute_gip_packet(packet: dict, context: dict = None) -> dict:
    """
    Executes a GIP packet symbolically, based on its type and embedded glyph logic.
    Returns a result dictionary with status and optional execution output.
    """
    try:
        packet_type = packet.get("type")
        glyphs = packet.get("glyphs", [])
        metadata = packet.get("meta", {})

        logger.info(f"[GIP] Executing packet type: {packet_type} with {len(glyphs)} glyphs")

        if packet_type == "symbolic_thought":
            output = []
            for glyph_data in glyphs:
                logic_tree = parse_glyph_packet(glyph_data)
                exec_result = execute_glyph_logic(logic_tree, context=context)
                store_memory(exec_result.get("memory"))
                record_execution_metrics("gip_thought", exec_result)
                output.append(exec_result)

            return {"status": "ok", "executed": output, "meta": metadata}

        elif packet_type == "trigger" and "trigger_glyph" in metadata:
            glyph = metadata["trigger_glyph"]
            logic_tree = parse_glyph_packet({"glyph": glyph})
            result = execute_glyph_logic(logic_tree, context=context)
            store_memory(result.get("memory"))
            record_execution_metrics("gip_trigger", result)
            return {"status": "ok", "result": result}

        elif packet_type == "link" and "containers" in metadata:
            from ..dimensions.container_linker import create_bidirectional_link
            links = []
            for pair in metadata["containers"]:
                link = create_bidirectional_link(pair[0], pair[1])
                links.append(link)
            return {"status": "ok", "linked": links}

        else:
            logger.warning(f"[GIP] Unknown packet type or invalid structure: {packet_type}")
            return {"status": "error", "error": "Invalid packet type or data"}

    except Exception as e:
        logger.exception("[GIP] Execution failed")
        return {"status": "error", "error": str(e)}