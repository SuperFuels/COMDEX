# 📁 backend/modules/glyphos/glyph_synthesis_engine.py

import hashlib
import json
from typing import List, Dict, Optional
from datetime import datetime

from backend.modules.glyphos.glyph_utils import parse_to_glyphos, summarize_to_glyph, generate_hash
from backend.modules.glyphos.glyph_grammar_inferencer import GlyphGrammarInferencer
from backend.modules.hexcore.memory_engine import store_memory_packet
from backend.modules.tessaris.tessaris_intent_executor import execute_glyph_packet
from backend.modules.consciousness.state_manager import STATE

# Optional WebSocket push
try:
    from modules.websocket_manager import WebSocketManager
    WS = WebSocketManager()
except:
    WS = None


class GlyphSynthesisEngine:
    def __init__(self):
        self.dedup_cache: Dict[str, Dict] = {}
        self.grammar_engine = GlyphGrammarInferencer()

    def compress_input(self, raw_text: str, source: str = "gpt") -> Dict:
        """
        Convert raw input into compressed glyph packet.
        source = 'gpt', 'goal', 'reflection', or 'mutation'
        """
        glyphs = parse_to_glyphos(raw_text)
        meaning_hash = generate_hash(glyphs)

        if meaning_hash in self.dedup_cache:
            return {
                "status": "duplicate",
                "hash": meaning_hash,
                "glyph_packet": self.dedup_cache[meaning_hash],
            }

        # Optional: Infer symbolic grammar
        inferred_grammar = []
        for g in glyphs:
            structure = self.grammar_engine.infer_from_glyph(g)
            if structure:
                inferred_grammar.append(structure)

        glyph_packet = {
            "source": source,
            "raw_input": raw_text,
            "glyphs": glyphs,
            "inferred_grammar": inferred_grammar,
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
        Includes inferred grammar metadata for HUD overlays.
        """
        if not WS:
            print("[WS] GlyphGrid WebSocket not available.")
            return

        payload = {
            "event": "glyph_injected",
            "data": {
                "glyphs": packet.get("glyphs", []),
                "grammar": packet.get("inferred_grammar", []),
                "timestamp": packet.get("timestamp"),
                "source": packet.get("source"),
                "hash": packet.get("hash")
            }
        }
        WS.broadcast(payload)

    def get_dedup_stats(self):
        return {
            "total_cached": len(self.dedup_cache),
            "recent_hashes": list(self.dedup_cache.keys())[-5:]
        }


# ✅ Singleton
glyph_synthesizer = GlyphSynthesisEngine()


def compress_to_glyphs(data: str) -> List[Dict]:
    """
    External utility wrapper to compress raw input into a list of glyphs.
    Returns only the glyph list, not the full packet.
    """
    result = glyph_synthesizer.compress_input(data)
    return result["glyph_packet"]["glyphs"]


# 🧪 Optional test stub
if __name__ == "__main__":
    sample = "The AI should generate a symbolic child using glyph logic and ethical alignment."
    result = glyph_synthesizer.compress_input(sample, source="child_generation")
    print("Glyph Packet:", json.dumps(result, indent=2))

    glyph_synthesizer.store_packet(result["glyph_packet"])
    glyph_synthesizer.inject_into_container(result["glyph_packet"], coord="2,0,0,0")
    glyph_synthesizer.push_to_glyph_grid(result["glyph_packet"])

    print("Execution result:", glyph_synthesizer.run_packet(result["glyph_packet"]))