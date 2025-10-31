import os
LITE = os.getenv("AION_LITE") == "1"
#!/usr/bin/env python3
# ================================================================
# 🌌 Glyph Synthesis Engine — Tessaris / AION Unified Compression v3
# ================================================================
"""
Enhancements:
- Enforced global uniqueness across all glyphs
- Deterministic SHA3-256 glyph generation + adaptive rehash for collisions
- Registry cross-check with glyph_storage
- Deduplication cache persistence
- Integrated with AION, Knowledge Graph, and Tessaris memory layers
"""
import os
import asyncio
import hashlib
import json
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from backend.modules.glyphos.glyph_utils import parse_to_glyphos, summarize_to_glyph, generate_hash
from backend.modules.glyphos.glyph_grammar_inferencer import GlyphGrammarInferencer
from backend.modules.glyphos.glyph_storage import get_glyph_registry, store_glyph_entry

from backend.modules.aion_resonance.semantic_estimator import (
    estimate_resonance,
    estimate_intensity,
    compute_SQI
)

# Core memory write always available
from backend.modules.hexcore.memory_engine import store_memory_packet

# Glyph constants
from backend.modules.glyphos.constants import GLYPH_ALPHABET, DEFAULT_GLYPH

# ================================================================
# 🌙 Lite Mode import gating
# ================================================================
import os
LITE = os.getenv("AION_LITE") == "1"

if not LITE:
    # Full consciousness + intent system
    from backend.modules.tessaris.tessaris_intent_executor import execute_glyph_packet
    from backend.modules.consciousness.state_manager import STATE
else:
    # Lightweight safe stubs
    def execute_glyph_packet(_):
        return "⚠️ Lite mode: execution disabled"

    class _LiteState:
        current_container = None
        def write_glyph_to_cube(self, *a, **k):
            return False

    STATE = _LiteState()

# --- Semantic overlay (ρ / Ī / SQI) ---
def _estimate_semantics(raw_text: str) -> dict:
    """
    Lightweight heuristics; replace with proper ResonantMemory/HMP when available.
    """
    try:
        from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
        RMC = ResonantMemoryCache()
        # crude sampling:
        sqi = max(0.55, min(0.95, 0.55 + (len(raw_text) % 100) / 1000))
        rho = max(0.4, min(0.95, (RMC.summary().get("rho_avg", 0.6))))
        I = max(0.4, min(0.95, (RMC.summary().get("entropy_avg", 0.5) * 0.8 + 0.2)))
    except Exception:
        sqi, rho, I = 0.62, 0.58, 0.52
    return {"SQI": round(sqi,3), "ρ": round(rho,3), "Ī": round(I,3)}

# ✅ Knowledge Graph integration
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.knowledge_graph.indexes.stats_index import build_stats_index

# Optional WebSocket push
try:
    from backend.modules.websocket_manager import WebSocketManager
    WS = WebSocketManager()
except Exception:
    WS = None

# ---------------------------------------------------------------
DEDUP_CACHE_FILE = Path(__file__).parent / "glyph_dedup_cache.json"

GLYPH_ALPHABET = (
    "⚛︎☯☀☾☽✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿❀❁❂❃❄❅❆❇❈❉❊❋"
    "⊕↔∇⟲μπΦΨΩΣΔΛΘΞΓαβγδλστωηικ"
    "◇◆◧◨◩◪◫⬡⬢⬣⬤⟁⧖"
)

# ================================================================
# 🔐 Deterministic + Collision-Proof Symbol Generator
# ================================================================
def generate_unique_symbol(base_text: str, context: str = "synthesis") -> str:
    """
    Deterministically generates a glyph symbol and ensures it’s globally unique.
    Uses SHA3-256 + adaptive rehashing on collision.

    We check against the **values** (stored glyph symbols) in the registry,
    not the keys (lemmas), so we never reissue an already assigned symbol.
    """
    registry = get_glyph_registry()
    # symbols currently in use (registry values)
    try:
        existing_symbols = {
            v.get("glyph")
            for v in registry.values()
            if isinstance(v, dict) and "glyph" in v
        }
    except Exception:
        # fallback if registry is a flat {lemma: glyph} map (older variants)
        existing_symbols = set(registry.values())

    salt = 0
    while True:
        key = f"{context}:{base_text}:{salt}".encode("utf-8")
        digest = hashlib.sha3_256(key).digest()
        idx = digest[0] % len(GLYPH_ALPHABET)
        candidate = GLYPH_ALPHABET[idx]
        if candidate not in existing_symbols:
            return candidate
        salt += 1

# ================================================================
# 🌐 Glyph Synthesis Engine
# ================================================================
class GlyphSynthesisEngine:
    def __init__(self):
        self.dedup_cache: Dict[str, Dict] = {}
        self.grammar_engine = GlyphGrammarInferencer()
        self._load_dedup_cache()

    # ───────────────────────────────
    # Cache
    # ───────────────────────────────
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

    # ───────────────────────────────
    # Compression pipeline
    # ───────────────────────────────
    def compress_input(self, raw_text: str, source: str = "gpt") -> Dict:
        """
        Convert raw text into a compressed glyph packet with globally unique glyphs.
        """
        glyphs = parse_to_glyphos(raw_text)
        meaning_hash = generate_hash(glyphs)

        # Deduplication: identical meaning returns cached result
        if meaning_hash in self.dedup_cache:
            return {
                "status": "duplicate",
                "hash": meaning_hash,
                "glyph_packet": self.dedup_cache[meaning_hash],
            }

        # Infer grammar structure
        inferred_grammar = []
        for g in glyphs:
            structure = self.grammar_engine.infer_from_glyph(g)
            if structure:
                inferred_grammar.append(structure)
        grammar_summary = list(set([s.get("type") for s in inferred_grammar if "type" in s]))

        # 🌌 Generate unique glyph symbol
        unique_symbol = generate_unique_symbol(raw_text, context=source)

        # === Semantic Overlay (ρ, Ī, SQI) ===
        from backend.modules.aion_resonance.semantic_estimator import (
            estimate_resonance, estimate_intensity, compute_SQI
        )

        rho = estimate_resonance(raw_text)
        I = estimate_intensity(raw_text)
        sqi = compute_SQI(rho, I)

        sem = {
            "rho": rho,
            "I": I,
            "SQI": sqi,
        }

        # 🧾 Construct glyph packet
        glyph_packet = {
            "source": source,
            "raw_input": raw_text,
            "glyphs": [unique_symbol],
            "inferred_grammar": inferred_grammar,
            "grammar_summary": grammar_summary,
            "hash": meaning_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "semantics": sem,  # ✅ semantic metadata
        }

        # 🔐 Register in GlyphOS global registry
        store_glyph_entry(raw_text, unique_symbol, metadata={"semantics": sem})

        # 🧠 Persist in dedup cache + memory
        self.dedup_cache[meaning_hash] = glyph_packet
        self._save_dedup_cache()

        store_memory_packet({
            "type": "glyph_registration",
            "lemma": raw_text,
            "glyph": unique_symbol,
            "rho": rho,
            "I": I,
            "SQI": sqi,
            "timestamp": glyph_packet["timestamp"]
        })

        return {"status": "new", "hash": meaning_hash, "glyph_packet": glyph_packet}
    # ───────────────────────────────
    # Memory / execution / grid ops
    # ───────────────────────────────
    def store_packet(self, packet: Dict, tag: Optional[str] = None):
        glyph_text = " ".join(packet["glyphs"]) if isinstance(packet["glyphs"], list) else str(packet["glyphs"])
        summary = summarize_to_glyph(glyph_text)
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

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(WS.broadcast(payload))
        except RuntimeError:
            # No loop active: fallback to sync fire-and-forget
            asyncio.run(WS.broadcast(payload))

    def mutate_packet(self, packet: Dict) -> Dict:
        mutated = dict(packet)
        mutated["glyphs"] = list(mutated["glyphs"])
        mutated["hash"] = generate_hash(mutated["glyphs"])
        mutated["source"] = "mutation"
        mutated["timestamp"] = datetime.utcnow().isoformat()
        return mutated

    def get_dedup_stats(self):
        return {
            "total_cached": len(self.dedup_cache),
            "recent_hashes": list(self.dedup_cache.keys())[-5:]
        }

    # ───────────────────────────────
    # 🧠 A5c Adaptive Synthesis
    # ───────────────────────────────
    def adaptive_synthesis(self):
        """Generate new symbolic glyphs from KG density + entropy."""
        kgw = get_kg_writer()
        stats = kgw.validate_knowledge_graph()
        total_glyphs = stats["total_glyphs"]
        entropy = stats["stats_index"]["summary"].get("entropy", 0.0)

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

# ================================================================
# 🧩 Global API
# ================================================================
glyph_synthesizer = GlyphSynthesisEngine()

def compress_to_glyphs(data: str) -> List[str]:
    result = glyph_synthesizer.compress_input(data)
    return result["glyph_packet"]["glyphs"]

def synthesize_glyphs_from_text(text: str, source: str = "manual") -> List[str]:
    result = glyph_synthesizer.compress_input(text, source)
    glyph_packet = result["glyph_packet"]
    glyph_synthesizer.store_packet(glyph_packet, tag=source)
    glyph_synthesizer.push_to_glyph_grid(glyph_packet)
    return glyph_packet["glyphs"]

# ================================================================
# 🧪 Test Mode
# ================================================================
if __name__ == "__main__":
    sample = "The AI should generate a symbolic child using glyph logic and ethical alignment."
    result = glyph_synthesizer.compress_input(sample, source="child_generation")
    print("Glyph Packet:", json.dumps(result, indent=2))

    glyph_synthesizer.store_packet(result["glyph_packet"])
    glyph_synthesizer.inject_into_container(result["glyph_packet"], coord="2,0,0,0")
    glyph_synthesizer.push_to_glyph_grid(result["glyph_packet"])
    print("Execution result:", glyph_synthesizer.run_packet(result["glyph_packet"]))

    mutated = glyph_synthesizer.mutate_packet(result["glyph_packet"])
    print("Mutated Packet:", json.dumps(mutated, indent=2))

    adaptive = glyph_synthesizer.adaptive_synthesis()
    print("Adaptive Packet:", json.dumps(adaptive, indent=2))