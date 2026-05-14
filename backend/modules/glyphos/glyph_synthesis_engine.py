#!/usr/bin/env python3
# ================================================================
# 🌌 Glyph Synthesis Engine - Tessaris / AION Unified Compression v3.1
# ================================================================
"""
Enhancements:
- Enforced global uniqueness across all glyphs (via storage bijection)
- Deterministic SHA3-256 glyph generation + adaptive, deterministic variants
- Registry cross-check with glyph_storage (reverse index aware)
- Deduplication cache persistence
- Integrated with AION, Knowledge Graph, and Tessaris memory layers
- Avoids reserved/operator glyphs; never redefines GLYPH_ALPHABET locally
"""

from __future__ import annotations

import os
import asyncio
import hashlib
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

# 🌙 Lite Mode flag (single source of truth)
LITE = os.getenv("AION_LITE") == "1"

from backend.modules.glyphos.glyph_utils import (
    parse_to_glyphos,
    summarize_to_glyph,
    generate_hash,
)
from backend.modules.glyphos.glyph_grammar_inferencer import GlyphGrammarInferencer
from backend.modules.glyphos.glyph_storage import (
    get_glyph_registry,
    store_glyph_entry,
)

# Session-level cache to ensure uniqueness within a single run (tests, batch jobs)
_SESSION_ASSIGNED: set[str] = set()

def _reset_session_glyph_cache():
    """Helper for tests if needed."""
    _SESSION_ASSIGNED.clear()

# Reverse registry is optional (supported in v2 storage); fall back if missing
try:
    from backend.modules.glyphos.glyph_storage import get_glyph_reverse_registry  # type: ignore
except Exception:
    def get_glyph_reverse_registry() -> Dict[str, str]:
        reg = get_glyph_registry()
        rev: Dict[str, str] = {}
        for lemma, entry in reg.items():
            glyph = entry.get("glyph") if isinstance(entry, dict) else entry
            if glyph:
                rev.setdefault(glyph, lemma)
        return rev

# Semantic estimators (we'll use our local _estimate_semantics wrapper)
from backend.modules.aion_resonance.semantic_estimator import (
    estimate_resonance,
    estimate_intensity,
    compute_SQI,
)

# Core memory write always available
from backend.modules.hexcore.memory_engine import store_memory_packet

# Glyph constants (authoritative alphabet + defaults)
from backend.modules.glyphos.constants import GLYPH_ALPHABET, DEFAULT_GLYPH

# ✅ Knowledge Graph integration
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.knowledge_graph.indexes.stats_index import build_stats_index

# Optional WebSocket push
try:
    from backend.modules.websocket_manager import WebSocketManager
    WS = WebSocketManager()
except Exception:
    WS = None

if os.getenv("GLYPHOS_QUIET", "0") == "1":
    WS = None  # silence WS broadcasts during bulk updates

# ---------------------------------------------------------------
DEDUP_CACHE_FILE = Path(__file__).parent / "glyph_dedup_cache.json"

# ---------------------------------------------------------------
# 🚫 Reserved glyphs (operators + photon reserved map)
# ---------------------------------------------------------------
_OPERATOR_GLYPHS = {"⊕", "↔", "∇", "⟲", "μ", "π"}

def _load_photon_reserved() -> set[str]:
    try:
        p = Path("backend/modules/photonlang/photon_reserved_map.json")
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            vals = set()
            for v in data.values():
                if isinstance(v, str):
                    vals.add(v)
                elif isinstance(v, list):
                    vals.update(x for x in v if isinstance(x, str))
            return vals
    except Exception:
        pass
    return set()

_RESERVED = _OPERATOR_GLYPHS | _load_photon_reserved()

def _filtered_alphabet() -> str:
    """Alphabet without reserved/operator symbols."""
    return "".join(ch for ch in GLYPH_ALPHABET if ch not in _RESERVED)

# --- Semantic overlay (ρ / Ī / SQI) ---
def _estimate_semantics(raw_text: str) -> dict:
    """
    Lightweight heuristics with graceful fallback.
    """
    try:
        # Prefer actual estimators if present
        rho = float(estimate_resonance(raw_text))
        I = float(estimate_intensity(raw_text))
        sqi = float(compute_SQI(rho, I))
        return {"SQI": round(sqi, 3), "ρ": round(rho, 3), "Ī": round(I, 3)}
    except Exception:
        # Fallback heuristic
        try:
            from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
            RMC = ResonantMemoryCache()
            sqi = max(0.55, min(0.95, 0.55 + (len(raw_text) % 100) / 1000))
            rho = max(0.4, min(0.95, (RMC.summary().get("rho_avg", 0.6))))
            I = max(0.4, min(0.95, (RMC.summary().get("entropy_avg", 0.5) * 0.8 + 0.2)))
        except Exception:
            sqi, rho, I = 0.62, 0.58, 0.52
        return {"SQI": round(sqi, 3), "ρ": round(rho, 3), "Ī": round(I, 3)}

# 🌙 Execution surfaces
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

# ================================================================
# 🔐 Deterministic + Collision-Averse Symbol Generator
# ================================================================
import hashlib
from backend.modules.glyphos.constants import RESERVED_GLYPHS, filtered_alphabet

# Session cache to ensure uniqueness within a single run (tests / batch jobs)
_SESSION_ASSIGNED: set[str] = set()

def reset_session_glyph_cache() -> None:
    _SESSION_ASSIGNED.clear()

def _encode_base_n(num: int, alphabet: str) -> str:
    """Encode an integer in base-|alphabet| using provided rune set."""
    base = len(alphabet)
    if base <= 1:
        raise RuntimeError("Alphabet must contain at least 2 runes.")
    out: list[str] = []
    if num == 0:
        return alphabet[0]
    while num:
        num, r = divmod(num, base)
        out.append(alphabet[r])
    return "".join(out)

def generate_unique_symbol(
    base_text: str,
    context: str = "synthesis",
    *,
    min_len: int = 1,
    max_len: int = 4,
    allow_repeats: bool = False,   # disallow "✱✱" by default
    track_session: bool = True,
) -> str:
    """
    Deterministic base-N mapping over a RESERVED-filtered alphabet.

    Process:
      * seed = SHA3-256(f"{context}:{base_text}:{salt}")
      * core = base-N(seed) over filtered alphabet
      * try lengths L ∈ [min_len..max_len]
      * skip: reserved runes (already filtered), session duplicates, registry duplicates,
              and repeated single-rune sequences (e.g., ✱✱) unless allow_repeats=True
      * on exhaustion, increment salt and retry (deterministic & collision-free)
    """
    assert min_len >= 1 and max_len >= min_len, "invalid length bounds"

    alpha = filtered_alphabet()  # already excludes RESERVED_GLYPHS + Greek + default
    if not alpha:
        raise RuntimeError("Filtered glyph alphabet is empty (over-reserved).")

    # Late import to avoid circulars during early boot
    from backend.modules.glyphos.glyph_storage import get_glyph_registry  # type: ignore

    reg = get_glyph_registry()
    # Support both {lemma: {"glyph": ...}} and legacy {lemma: "glyph"}
    in_use: set[str] = set()
    for v in reg.values():
        in_use.add(v.get("glyph") if isinstance(v, dict) else v)

    salt = 0
    while True:
        h = hashlib.sha3_256(f"{context}:{base_text}:{salt}".encode("utf-8")).digest()
        num = int.from_bytes(h, "big")
        core = _encode_base_n(num, alpha)

        for L in range(min_len, max_len + 1):
            cand = core[:L] if L <= len(core) else core  # no zero-pad; deterministic slice

            # Skip sequences like "✱✱" when repeats are not allowed
            if not allow_repeats and len(cand) > 1 and len(set(cand)) == 1:
                continue

            if track_session and cand in _SESSION_ASSIGNED:
                continue

            # Extra safety: in theory alpha already avoids RESERVED, but double-check
            if any(ch in RESERVED_GLYPHS for ch in cand):
                continue

            if cand in in_use:
                continue

            if track_session:
                _SESSION_ASSIGNED.add(cand)
            return cand

        salt += 1
# ================================================================
# 🌐 Glyph Synthesis Engine
# ================================================================
class GlyphSynthesisEngine:
    def __init__(self):
        self.dedup_cache: Dict[str, Dict[str, Any]] = {}
        self.grammar_engine = GlyphGrammarInferencer()
        self._load_dedup_cache()

    # ───────────────────────────────
    # Cache
    # ───────────────────────────────
    def _load_dedup_cache(self):
        if DEDUP_CACHE_FILE.exists():
            try:
                with open(DEDUP_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.dedup_cache = json.load(f)
            except Exception:
                self.dedup_cache = {}

    def _save_dedup_cache(self):
        try:
            with open(DEDUP_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.dedup_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Failed to save dedup cache: {e}")

    # ───────────────────────────────
    # Compression pipeline
    # ───────────────────────────────
    def compress_input(self, raw_text: str, source: str = "gpt") -> Dict[str, Any]:
        """
        Convert raw text into a compressed glyph packet with globally unique glyphs.
        """
        glyphs = parse_to_glyphos(raw_text)
        meaning_hash = generate_hash(glyphs)

        # Deduplication: identical meaning returns cached packet (immutable)
        if meaning_hash in self.dedup_cache:
            return {
                "status": "duplicate",
                "hash": meaning_hash,
                "glyph_packet": self.dedup_cache[meaning_hash],
            }

        # Infer grammar structure
        inferred_grammar: List[Dict[str, Any]] = []
        for g in glyphs:
            try:
                structure = self.grammar_engine.infer_from_glyph(g)
                if structure:
                    inferred_grammar.append(structure)
            except Exception:
                # non-fatal: skip bad nodes
                continue

        grammar_summary = sorted({s.get("type") for s in inferred_grammar if isinstance(s, dict) and "type" in s})

        # 🌌 Generate proposal (storage guarantees final uniqueness)
        proposed_symbol = generate_unique_symbol(raw_text, context=source)

        # === Semantic Overlay (ρ, Ī, SQI) ===
        sem = _estimate_semantics(raw_text)
        # keep both classic + pretty keys for downstream compatibility
        rho, I, sqi = sem.get("ρ"), sem.get("Ī"), sem.get("SQI")

        # 🔐 Register in GlyphOS global registry (bijective, atomic)
        store_res = store_glyph_entry(
            lemma=raw_text,
            glyph=proposed_symbol,
            metadata={"semantics": {"rho": rho, "I": I, "SQI": sqi}},
        )
        assigned_symbol = store_res.get("glyph", proposed_symbol)
        registry_reason = store_res.get("reason", "created")

        # 🧾 Construct glyph packet
        glyph_packet: Dict[str, Any] = {
            "source": source,
            "raw_input": raw_text,
            "glyphs": [assigned_symbol],
            "inferred_grammar": inferred_grammar,
            "grammar_summary": list(grammar_summary),
            "hash": meaning_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "semantics": {"rho": rho, "I": I, "SQI": sqi},
            "registry_reason": registry_reason,
        }

        # 🧠 Persist in dedup cache + memory
        self.dedup_cache[meaning_hash] = glyph_packet
        self._save_dedup_cache()

        store_memory_packet({
            "type": "glyph_registration",
            "lemma": raw_text,
            "glyph": assigned_symbol,
            "rho": rho,
            "I": I,
            "SQI": sqi,
            "timestamp": glyph_packet["timestamp"],
            "reason": registry_reason,
        })

        return {"status": "new", "hash": meaning_hash, "glyph_packet": glyph_packet}
    # ───────────────────────────────
    # Memory / execution / grid ops
    # ───────────────────────────────
    def store_packet(self, packet: Dict, tag: Optional[str] = None):
        glyphs = packet.get("glyphs", [])
        glyph_text = " ".join(glyphs) if isinstance(glyphs, list) else str(glyphs)
        summary = summarize_to_glyph(glyph_text)

        store_memory_packet({
            "type": "glyph_compression",
            "summary": summary,
            "glyphs": glyphs,
            "grammar": packet.get("grammar_summary", []),
            "semantics": packet.get("semantics", {}),
            "data": packet,
            "tag": tag or packet.get("source", "unknown"),
            "timestamp": packet.get("timestamp"),
            "hash": packet.get("hash"),
        })

    def run_packet(self, packet: Dict) -> str:
        glyphs = packet.get("glyphs")
        if not glyphs:
            return "❌ No glyphs to execute."
        # In Lite mode execute_glyph_packet returns a safe notice
        return execute_glyph_packet(glyphs)

    def inject_into_container(self, packet: Dict, coord: str = "0,0,0,0") -> bool:
        try:
            container_id = STATE.current_container.get("id") if getattr(STATE, "current_container", None) else None
        except Exception:
            container_id = None

        if not container_id:
            print("[❌] No active container to inject glyph into.")
            return False

        glyphs = packet.get("glyphs", [])
        if not glyphs:
            print("[⚠️] Cannot inject empty glyph packet.")
            return False

        main_glyph = glyphs[0]
        try:
            success = STATE.write_glyph_to_cube(container_id, coord, main_glyph)
        except Exception as e:
            print(f"[❌] Glyph injection failed: {e}")
            return False

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
                "hash": packet.get("hash"),
                "semantics": packet.get("semantics", {}),
            }
        }

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(WS.broadcast(payload))
        except RuntimeError:
            # No loop active: run a temporary loop
            try:
                asyncio.run(WS.broadcast(payload))
            except Exception as e:
                print(f"[WS] Broadcast failed: {e}")

    def mutate_packet(self, packet: Dict) -> Dict:
        mutated = dict(packet)
        mutated["glyphs"] = list(mutated.get("glyphs", []))
        mutated["hash"] = generate_hash(mutated["glyphs"])
        mutated["source"] = "mutation"
        mutated["timestamp"] = datetime.utcnow().isoformat()
        # keep semantics/grammar as-is; mutations are symbolic not re-registered
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
        try:
            kgw = get_kg_writer()
            stats = kgw.validate_knowledge_graph()
            total_glyphs = stats.get("total_glyphs", 0)
            entropy = stats.get("stats_index", {}).get("summary", {}).get("entropy", 0.0)
        except Exception:
            total_glyphs, entropy = 0, 0.0

        if total_glyphs > 500 or entropy > 0.7:
            seed_text = "Initiate reflective mutation and self-alignment."
        elif total_glyphs < 100:
            seed_text = "Bootstrap foundational reasoning and symbolic growth."
        else:
            seed_text = "Balance entanglement, collapse, and mutation."

        print(f"[🧠 Adaptive Synthesis] Density={total_glyphs}, Entropy={entropy:.2f} -> Seed: {seed_text}")
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
    print("Glyph Packet:", json.dumps(result["glyph_packet"], indent=2, ensure_ascii=False))

    glyph_synthesizer.store_packet(result["glyph_packet"])
    glyph_synthesizer.inject_into_container(result["glyph_packet"], coord="2,0,0,0")
    glyph_synthesizer.push_to_glyph_grid(result["glyph_packet"])
    print("Execution result:", glyph_synthesizer.run_packet(result["glyph_packet"]))

    mutated = glyph_synthesizer.mutate_packet(result["glyph_packet"])
    print("Mutated Packet:", json.dumps(mutated, indent=2, ensure_ascii=False))

    adaptive = glyph_synthesizer.adaptive_synthesis()
    print("Adaptive Packet:", json.dumps(adaptive, indent=2, ensure_ascii=False))