import hashlib
import json
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from backend.modules.glyphos.glyph_utils import parse_to_glyphos, summarize_to_glyph, generate_hash
from backend.modules.glyphos.glyph_grammar_inferencer import GlyphGrammarInferencer
from backend.modules.hexcore.memory_engine import store_memory_packet
from backend.modules.tessaris.tessaris_intent_executor import execute_glyph_packet
from backend.modules.consciousness.state_manager import STATE

# ✅ NEW: Knowledge Graph integration for A5c
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.knowledge_graph.indexes.stats_index import build_stats_index

# Optional WebSocket push
try:
    from backend.modules.websocket_manager import WebSocketManager
    WS = WebSocketManager()
except:
    WS = None

DEDUP_CACHE_FILE = Path(__file__).parent / "glyph_dedup_cache.json"


class GlyphSynthesisEngine:
    def __init__(self):
        self.dedup_cache: Dict[str, Dict] = {}
        self.grammar_engine = GlyphGrammarInferencer()
        self._load_dedup_cache()

    def _load_dedup_cache(self):
        if DEDUP_CACHE_FILE.exists():
            try:
                with open(DEDUP_CACHE_FILE, "r") as f:
                    self.dedup_cache = json.load(f)
            except Exception:
                self.dedup_cache = {}

    def _save_dedup_cache(self):
        try:
            with open(DEDUP_CACHE_FILE, "w") as f:
                json.dump(self.dedup_cache, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save dedup cache: {e}")

    def compress_input(self, raw_text: str, source: str = "gpt") -> Dict:
        """
        Convert raw input into compressed glyph packet.
        source = 'gpt', 'goal', 'reflection', 'mutation', or 'lean'
        """
        glyphs = parse_to_glyphos(raw_text)
        meaning_hash = generate_hash(glyphs)

        if meaning_hash in self.dedup_cache:
            return {
                "status": "duplicate",
                "hash": meaning_hash,
                "glyph_packet": self.dedup_cache[meaning_hash],
            }

        inferred_grammar = []
        for g in glyphs:
            structure = self.grammar_engine.infer_from_glyph(g)
            if structure:
                inferred_grammar.append(structure)

        grammar_summary = list(set([s.get("type") for s in inferred_grammar if "type" in s]))

        glyph_packet = {
            "source": source,
            "raw_input": raw_text,
            "glyphs": glyphs,
            "inferred_grammar": inferred_grammar,
            "grammar_summary": grammar_summary,
            "hash": meaning_hash,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.dedup_cache[meaning_hash] = glyph_packet
        self._save_dedup_cache()

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
            "grammar": packet.get("grammar_summary", []),
            "data": packet,
            "tag": tag or packet.get("source", "unknown"),
        })

    def run_packet(self, packet: Dict) -> str:
        if not packet.get("glyphs"):
            return "❌ No glyphs to execute."
        return execute_glyph_packet(packet["glyphs"])

    def inject_into_container(self, packet: Dict, coord: str = "0,0,0,0") -> bool:
        container_id = STATE.current_container.get("id") if STATE.current_container else None
        if not container_id:
            print("[❌] No active container to inject glyph into.")
            return False

        glyphs = packet.get("glyphs", [])
        if not glyphs:
            print("[⚠️] Cannot inject empty glyph packet.")
            return False

        main_glyph = glyphs[0]
        success = STATE.write_glyph_to_cube(container_id, coord, main_glyph)

        if success:
            print(f"[📦] Glyph {main_glyph} injected at {coord} into container {container_id}")
        else:
            print("[❌] Glyph injection failed.")
        return success

    def push_to_glyph_grid(self, packet: Dict):
        if not WS:
            print("[WS] GlyphGrid WebSocket not available.")
            return

        payload = {
            "event": "glyph_injected",
            "data": {
                "glyphs": packet.get("glyphs", []),
                "grammar": packet.get("inferred_grammar", []),
                "summary": packet.get("grammar_summary", []),
                "timestamp": packet.get("timestamp"),
                "source": packet.get("source"),
                "hash": packet.get("hash")
            }
        }
        WS.broadcast(payload)

    def mutate_packet(self, packet: Dict) -> Dict:
        mutated = dict(packet)
        mutated_glyphs = list(mutated["glyphs"])
        if len(mutated_glyphs) > 1:
            mutated_glyphs.reverse()
        mutated["glyphs"] = mutated_glyphs
        mutated["hash"] = generate_hash(mutated_glyphs)
        mutated["source"] = "mutation"
        mutated["timestamp"] = datetime.utcnow().isoformat()
        return mutated

    def get_dedup_stats(self):
        return {
            "total_cached": len(self.dedup_cache),
            "recent_hashes": list(self.dedup_cache.keys())[-5:]
        }

    # ────────────────────────────────────────────────
    # 🧠 A5c: Adaptive Glyph Synthesis from KG
    # ────────────────────────────────────────────────
    def adaptive_synthesis(self):
        """
        Dynamically synthesize glyphs based on Knowledge Graph density and entropy.
        """
        kgw = get_kg_writer()
        stats = kgw.validate_knowledge_graph()
        total_glyphs = stats["total_glyphs"]
        entropy = stats["stats_index"]["summary"].get("entropy", 0.0)

        # Define thresholds
        if total_glyphs > 500 or entropy > 0.7:
            seed_text = "Initiate reflective mutation and self-alignment."
        elif total_glyphs < 100:
            seed_text = "Bootstrap foundational reasoning and symbolic growth."
        else:
            seed_text = "Balance entanglement, collapse, and mutation."

        print(f"[🧠 Adaptive Synthesis] Density={total_glyphs}, Entropy={entropy:.2f} → Seed: {seed_text}")

        packet = self.compress_input(seed_text, source="adaptive_synthesis")["glyph_packet"]
        self.store_packet(packet, tag="adaptive")
        self.push_to_glyph_grid(packet)
        return packet


# ✅ Singleton
glyph_synthesizer = GlyphSynthesisEngine()


def compress_to_glyphs(data: str) -> List[Dict]:
    result = glyph_synthesizer.compress_input(data)
    return result["glyph_packet"]["glyphs"]


def synthesize_glyphs_from_text(text: str, source: str = "manual") -> List[Dict]:
    result = glyph_synthesizer.compress_input(text, source)
    glyph_packet = result["glyph_packet"]
    glyph_synthesizer.store_packet(glyph_packet, tag=source)
    glyph_synthesizer.push_to_glyph_grid(glyph_packet)
    return glyph_packet["glyphs"]


# 🧪 Optional test stub
if __name__ == "__main__":
    sample = "The AI should generate a symbolic child using glyph logic and ethical alignment."
    result = glyph_synthesizer.compress_input(sample, source="child_generation")
    print("Glyph Packet:", json.dumps(result, indent=2))

    glyph_synthesizer.store_packet(result["glyph_packet"])
    glyph_synthesizer.inject_into_container(result["glyph_packet"], coord="2,0,0,0")
    glyph_synthesizer.push_to_glyph_grid(result["glyph_packet"])
    print("Execution result:", glyph_synthesizer.run_packet(result["glyph_packet"]))

    # 🧬 Test mutation
    mutated = glyph_synthesizer.mutate_packet(result["glyph_packet"])
    print("Mutated Packet:", json.dumps(mutated, indent=2))

    # 🧠 Test adaptive synthesis
    adaptive = glyph_synthesizer.adaptive_synthesis()
    print("Adaptive Packet:", json.dumps(adaptive, indent=2))