# backend/modules/glyphos/glyph_synthesis_engine.py

import hashlib
import json
from typing import List, Dict, Optional
from datetime import datetime

from modules.glyphos.glyph_utils import parse_to_glyphos, summarize_to_glyph, generate_hash
from modules.memory.memory_engine import store_memory_packet
from modules.tessaris.tessaris_engine import execute_glyph_packet
from modules.consciousness.state_manager import STATE

# Optional WebSocket push
try:
    from modules.websocket_manager import WebSocketManager
    WS = WebSocketManager()
except:
    WS = None


class GlyphSynthesisEngine:
    def __init__(self):
        self.dedup_cache: Dict[str, Dict] = {}

    def compress_input(self, raw_text: str, source: str = "gpt") -> Dict:
        """
        Convert raw input into compressed glyph packet.
        source = 'gpt', 'goal', or 'reflection'
        """
        glyphs = parse_to_glyphos(raw_text)
        meaning_hash = generate_hash(glyphs)

        if meaning_hash in self.dedup_cache:
            return {
                "status": "duplicate",
                "hash": meaning_hash,
                "glyph_packet": self.dedup_cache[meaning_hash],
            }

        glyph_packet = {
            "source": source,
            "raw_input": raw_text,
            "glyphs": glyphs,
            "hash": meaning_hash,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.dedup_cache[meaning_hash] = glyph_packet
        return {
            "status": "new",
            "hash": meaning_hash,
            "glyph_packet": glyph_packet,
        }

    def store_packet(self, packet: Dict, tag: Optional[str] = None):
        summary = summarize_to_glyph(packet["glyphs"])
        store_memory_packet({
            "type": "glyph_compression",
            "summary": summary,
            "data": packet,
            "tag": tag or packet.get("source", "unknown"),
        })

    def run_packet(self, packet: Dict) -> str:
        return execute_glyph_packet(packet["glyphs"])

    def inject_into_container(self, packet: Dict, coord: str = "0,0,0,0") -> bool:
        """
        Store the glyph packet into the active container at specified coord.
        """
        container_id = STATE.current_container.get("id") if STATE.current_container else None
        if not container_id:
            print("[❌] No active container to inject glyph into.")
            return False

        # Use first glyph as entry point
        main_glyph = packet["glyphs"][0] if packet["glyphs"] else "⚙"
        success = STATE.write_glyph_to_cube(container_id, coord, main_glyph)

        if success:
            print(f"[📦] Glyph {main_glyph} injected at {coord} into container {container_id}")
        return success

    def push_to_glyph_grid(self, packet: Dict):
        """
        Push synthesized glyphs to glyph grid via WebSocket.
        """
        if not WS:
            print("[WS] GlyphGrid WebSocket not available.")
            return

        payload = {
            "event": "glyph_injected",
            "data": {
                "glyphs": packet.get("glyphs", []),
                "timestamp": packet.get("timestamp"),
                "source": packet.get("source"),
            }
        }
        WS.broadcast(payload)


# ✅ Singleton
glyph_synthesizer = GlyphSynthesisEngine()


# 🧪 Optional test stub
if __name__ == "__main__":
    sample = "The AI should reflect on her past decision and improve ethical alignment."
    result = glyph_synthesizer.compress_input(sample, source="reflection")
    print("Glyph Packet:", json.dumps(result, indent=2))

    glyph_synthesizer.store_packet(result["glyph_packet"])
    glyph_synthesizer.inject_into_container(result["glyph_packet"], coord="1,0,0,0")
    glyph_synthesizer.push_to_glyph_grid(result["glyph_packet"])

    print("Execution result:", glyph_synthesizer.run_packet(result["glyph_packet"]))