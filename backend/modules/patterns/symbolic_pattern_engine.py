from __future__ import annotations

import json
import logging
from typing import List, Dict, Any, Optional, Sequence, Union, TYPE_CHECKING

logger = logging.getLogger(__name__)

# Optional SCI overlay (safe fallback)
try:
    from backend.modules.aion_language.sci_overlay import sci_emit  # type: ignore
except Exception:  # pragma: no cover
    def sci_emit(*a, **k):  # type: ignore
        pass


if TYPE_CHECKING:
    # Only for type hints; NOT executed at runtime (avoids circular imports)
    from .pattern_registry import Pattern, PatternRegistry  # noqa: F401


class SymbolicPatternEngine:
    def __init__(self):
        # 🚫 IMPORTANT: deferred imports to break circular import chains
        from .pattern_registry import PatternRegistry  # local import
        from backend.modules.glyphvault.soul_law_validator import SoulLawValidator
        from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
        from backend.modules.patterns.pattern_websocket_broadcast import PatternWebSocketBroadcaster
        from backend.modules.patterns.pattern_qfc_bridge import PatternQFCBridge

        self.registry = PatternRegistry()
        self.validator = SoulLawValidator()
        self.kg_writer = KnowledgeGraphWriter()
        self.qfc_bridge = PatternQFCBridge()
        self.broadcaster = PatternWebSocketBroadcaster()

    def detect_patterns(
        self,
        glyphs: List[Dict[str, Any]],
        container_id: str = "unknown",
        container: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detects known patterns in a flat list of glyphs.
        Returns list of matched pattern dictionaries.
        """
        # Deferred imports (avoid import-time cycles)
        from time import time
        from backend.modules.patterns.pattern_emotion_bridge import trigger_emotion_from_pattern
        from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
        from backend.modules.sqi.sqi_stability_trace import record_sqi_delta
        from .pattern_registry import stringify_glyph

        matches: List[Dict[str, Any]] = []

        # --- Preprocess glyphs ---
        processed_glyphs: List[Dict[str, Any]] = []
        for glyph in glyphs:
            if glyph.get("type") == "symbol" and "text" in glyph:
                expanded = tokenize_symbol_text_to_glyphs(glyph["text"])
                processed_glyphs.extend(expanded)
            else:
                processed_glyphs.append(glyph)
        glyphs = processed_glyphs

        # --- Load patterns ---
        all_patterns = self.registry.get_all_patterns()

        # --- Detection loop ---
        for pattern in all_patterns:
            if self._pattern_matches(pattern, glyphs):
                # ✅ MATCH
                sqi = self.evaluate_pattern_sqi(pattern)
                pattern.sqi_score = sqi

                # ✅ RMC resonance boost
                try:
                    from backend.modules.resonant_memory.resonant_memory_cache import ResonantMemoryCache
                    rmc = ResonantMemoryCache()

                    glyph_ids = [g.get("id") or stringify_glyph(g) for g in pattern.glyphs]
                    resonance_vals: List[float] = []
                    for g in glyph_ids:
                        entry = rmc.recall(str(g).lower())
                        if entry and isinstance(entry, dict):
                            val = entry.get("stability") or entry.get("coherence") or entry.get("SQI_avg")
                            if isinstance(val, (int, float)):
                                resonance_vals.append(float(val))

                    if resonance_vals:
                        r_boost = sum(resonance_vals) / len(resonance_vals)
                        pattern.sqi_score = round(float(pattern.sqi_score) * (1 + r_boost * 0.15), 4)
                        pattern.metadata["resonance_boost"] = r_boost
                except Exception:
                    pass

                # Convert -> dict
                pattern_dict = pattern.to_dict()
                pattern_dict["matched_in"] = container_id
                matches.append(pattern_dict)

                # Side effects if real container
                if container:
                    self.inject_pattern_trace(container, pattern_dict)
                    try:
                        self.broadcaster.broadcast_pattern_detected(pattern)
                    except Exception:
                        pass
                    try:
                        self.qfc_bridge.trigger_qfc_from_pattern(pattern_dict, container)
                    except Exception:
                        pass
                    try:
                        trigger_emotion_from_pattern(pattern_dict, container)
                    except Exception:
                        pass

                # Predictive output
                try:
                    self.broadcaster.broadcast_pattern_prediction(pattern.name, glyphs)
                except Exception:
                    pass

            else:
                # ❌ NOT MATCHED - check collapse
                sqi_val = float(getattr(pattern, "sqi_score", 0.3) or 0.3)
                if sqi_val < 0.15:
                    try:
                        sci_emit(
                            "pattern_collapse",
                            {
                                "pattern_id": pattern.pattern_id,
                                "name": pattern.name,
                                "type": pattern.type,
                                "sqi": sqi_val,
                                "timestamp": time(),
                                "state": "collapse",
                            },
                        )
                    except Exception:
                        pass

                    # ✅ SQI Stability logging for collapse
                    try:
                        record_sqi_delta(-abs(sqi_val), source="pattern_collapse")
                    except Exception:
                        pass

        return matches

    def _pattern_matches(self, pattern: "Pattern", glyphs: List[Any]) -> bool:
        """
        Check if the container glyphs include the pattern glyphs in exact order.
        """
        from .pattern_registry import stringify_glyph  # deferred import

        glyph_str_sequence = [stringify_glyph(g) for g in glyphs]
        pattern_str_sequence = [stringify_glyph(g) for g in pattern.glyphs]

        if len(glyph_str_sequence) < len(pattern_str_sequence):
            return False

        for i in range(len(glyph_str_sequence) - len(pattern_str_sequence) + 1):
            if glyph_str_sequence[i : i + len(pattern_str_sequence)] == pattern_str_sequence:
                return True

        return False

    def suggest_missing_glyphs(self, container: Dict[str, Any]) -> List[str]:
        """
        Given a container, suggest glyphs that complete or stabilize known patterns.
        """
        from backend.modules.patterns.pattern_utils import extract_all_glyphs
        from .pattern_registry import stringify_glyph

        glyphs = extract_all_glyphs(container.get("symbolic_tree", {}))
        glyphs_str = [stringify_glyph(g) for g in glyphs]
        suggestions = set()

        # --- existing pattern fill suggestions ---
        for pattern in self.registry.get_all_patterns():
            pattern_strs = [stringify_glyph(g) for g in pattern.glyphs]
            overlap = sum(p in glyphs_str for p in pattern_strs)
            if 0 < overlap < len(pattern_strs):
                for p in pattern_strs:
                    if p not in glyphs_str:
                        suggestions.add(p)

        # --- resonance-graph weighted neighbors ---
        try:
            from backend.modules.resonant_memory.resonant_memory_cache import ResonantMemoryCache
            rmc = ResonantMemoryCache()
            links = getattr(rmc, "cache", {}).get("links", {}) or {}
            neighbor_scores: Dict[str, float] = {}

            for g in glyphs_str:
                lg = str(g).lower()
                for key, entry in links.items():
                    if lg in key:
                        other = [k for k in key.split("↔") if k != lg]
                        if not other:
                            continue
                        o = other[0]
                        score = float((entry or {}).get("SQI_avg", 0.0) or 0.0)
                        neighbor_scores[o] = max(neighbor_scores.get(o, 0.0), score)

            for candidate, score in neighbor_scores.items():
                if score >= 0.35:
                    suggestions.add(candidate)

        except Exception as e:
            print(f"⚠️ RMC neighbor expansion failed: {e}")

        return sorted(suggestions)

    def _soullaw_ready_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Patterns are not beams, but SoulLaw expects beam-like context.
        Ensure required context fields exist so ethics checks don't false-fail.
        """
        from time import time

        event = dict(payload or {})

        md = event.get("metadata")
        if not isinstance(md, dict):
            md = {}
        ctx = md.get("context")
        if not isinstance(ctx, dict):
            ctx = {}

        # --- avatar state (prevents missing_avatar_state) ---
        ctx.setdefault("avatar_id", "system_root")
        ctx.setdefault("avatar_state", "active")
        ctx.setdefault("avatar_state_ts", time())

        # --- container meta (prevents invalid_container_metadata) ---
        cid = (
            ctx.get("container_id")
            or event.get("matched_in")
            or event.get("source_container")
            or "unknown"
        )
        ctx["container_id"] = cid

        cm = ctx.get("container_meta")
        if not isinstance(cm, dict):
            ctx["container_meta"] = {
                "id": cid,
                "kind": ctx.get("container_kind", "patterns"),
                "source": ctx.get("container_source", "symbolic_pattern_engine"),
            }

        md["context"] = ctx
        event["metadata"] = md

        # --- optional: provide minimal logic_tree so downstream hooks don't skip ---
        if not isinstance(event.get("logic_tree"), dict):
            event["logic_tree"] = {
                "∅": [{"pattern_id": event.get("pattern_id"), "name": event.get("name")}]
            }

        return event

    def validate_pattern_ethics(self, pattern: Dict[str, Any]) -> bool:
        """
        Uses SoulLaw to verify the pattern doesn't violate ethical constraints.
        """
        try:
            event = self._soullaw_ready_event(pattern)
            return bool(self.validator.validate_beam_event(event))
        except Exception:
            return False

    def mutate_pattern(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a mutated version of a pattern using resonance-guided mutation.
        """
        from .pattern_registry import Pattern, stringify_glyph  # deferred import
        from random import random
        from time import time

        # --- Resonance-guided mutation source ---
        try:
            from backend.modules.resonant_memory.resonant_memory_cache import ResonantMemoryCache
            rmc = ResonantMemoryCache()
        except Exception:
            rmc = None

        base_glyphs = pattern.get("glyphs", [])
        glyph_texts = [stringify_glyph(g) for g in base_glyphs]

        candidates: Dict[str, float] = {}

        if rmc and hasattr(rmc, "cache"):
            links = rmc.cache.get("links", {}) or {}
            for g in glyph_texts:
                gl = (g or "").lower().strip()
                for key, entry in links.items():
                    if gl in key:
                        other = [k for k in key.split("↔") if k != gl]
                        if other:
                            cand = other[0]
                            sqi = float((entry or {}).get("SQI_avg", 0.0) or 0.0)
                            candidates[cand] = max(candidates.get(cand, 0.0), sqi)

        mutated_glyphs: List[Dict[str, Any]] = []
        changed = False

        for g in glyph_texts:
            substitute = g
            for cand, weight in candidates.items():
                if weight > 0.35 and random() < min(weight, 0.8):
                    substitute = cand
                    changed = True
                    break
            mutated_glyphs.append({"text": substitute})

        if not changed:
            mutated_glyphs = self._shuffle_glyphs(base_glyphs)  # type: ignore

        mutated_pattern = Pattern(
            name=str(pattern.get("name", "pattern")) + "_mutated",
            glyphs=mutated_glyphs,
            pattern_type=pattern.get("type", pattern.get("pattern_type", "unknown")),
            trigger_logic=pattern.get("trigger_logic", ""),
            source_container=pattern.get("source_container"),
            metadata={"mutation_origin": pattern.get("pattern_id")},
        )

        mutated_pattern.sqi_score = self.evaluate_pattern_sqi(mutated_pattern)

        original_sqi = float(pattern.get("sqi_score", 0.3) or 0.3)
        new_sqi = float(mutated_pattern.sqi_score or 0.0)
        delta = round(new_sqi - original_sqi, 4)

        try:
            sci_emit(
                "pattern_mutation",
                {
                    "pattern_id": pattern.get("pattern_id"),
                    "name": pattern.get("name"),
                    "type": pattern.get("type"),
                    "origin_sqi": original_sqi,
                    "new_sqi": new_sqi,
                    "delta": delta,
                    "timestamp": time(),
                },
            )
        except Exception:
            pass

        try:
            from backend.modules.resonant_memory.resonant_memory_cache import ResonantMemoryCache
            rmc2 = ResonantMemoryCache()
            rmc2.push_sample(
                rho=new_sqi,
                entropy=abs(delta),
                sqi=new_sqi,
                delta=delta,
                source="pattern_mutation",
            )
        except Exception:
            pass

        try:
            from backend.modules.sqi.sqi_stability_trace import record_sqi_delta
            record_sqi_delta(delta, source="pattern_mutation")
        except Exception:
            pass

        return mutated_pattern.to_dict()

    def _shuffle_glyphs(self, glyphs: Sequence[Any]) -> List[Any]:
        from random import shuffle
        new_glyphs = list(glyphs)
        shuffle(new_glyphs)
        return new_glyphs

    def evaluate_pattern_sqi(self, pattern: Union["Pattern", Dict[str, Any]]) -> float:
        # Deferred import (prevents circular init issues)
        from backend.modules.sqi.sqi_scorer import score_pattern_sqi

        if hasattr(pattern, "to_dict"):
            return score_pattern_sqi(pattern.to_dict())  # type: ignore
        return score_pattern_sqi(pattern)

    def inject_pattern_trace(self, container: Dict[str, Any], pattern: Dict[str, Any]) -> None:
        """
        Injects a matched pattern trace into the container's metadata and writes it to KG.
        """
        trace = {
            "pattern_id": pattern["pattern_id"],
            "name": pattern["name"],
            "glyphs": pattern["glyphs"],
            "sqi_score": pattern["sqi_score"],
            "detected_at": container.get("tick", -1),
        }
        container.setdefault("patterns", []).append(trace)
        try:
            self.kg_writer.inject_pattern(
                container_id=container.get("container_id"),
                pattern_trace=trace,
            )
        except Exception:
            pass

    def replay_pattern_trace(self, container: Dict[str, Any], pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and return a previously detected pattern trace.
        """
        for pattern in container.get("patterns", []):
            if pattern.get("pattern_id") == pattern_id:
                return pattern
        return None

    def register_new_pattern(
        self,
        glyphs: List[Any],
        name: str,
        pattern_type: str,
        trigger_logic: str,
        source_container: str,
    ) -> Dict[str, Any]:
        """
        Save a new symbolic pattern to the registry and emit lifecycle event.
        """
        from time import time
        from .pattern_registry import Pattern  # deferred import

        new_pattern = Pattern(
            name=name,
            glyphs=glyphs,
            pattern_type=pattern_type,
            trigger_logic=trigger_logic,
            source_container=source_container,
        )

        new_pattern.sqi_score = self.evaluate_pattern_sqi(new_pattern)
        self.registry.register(new_pattern)

        try:
            sci_emit(
                "pattern_birth",
                {
                    "pattern_id": new_pattern.pattern_id,
                    "name": new_pattern.name,
                    "type": new_pattern.type,
                    "sqi": new_pattern.sqi_score,
                    "timestamp": time(),
                    "state": "birth",
                },
            )
        except Exception:
            pass

        try:
            from backend.modules.sqi.sqi_stability_trace import record_sqi_delta
            record_sqi_delta(0.0, source="pattern_birth")
        except Exception:
            pass

        return new_pattern.to_dict()

    def validate_pattern_ethics(self, pattern: Dict[str, Any]) -> bool:
        """
        Uses SoulLaw to verify the pattern doesn't violate ethical constraints.
        """
        try:
            return bool(self.validator.validate_beam_event(pattern))
        except Exception:
            return False

    def export_patterns(self) -> str:
        """
        Export all known patterns in JSON for review or training.
        """
        return json.dumps([p.to_dict() for p in self.registry.get_all_patterns()], indent=2)


# Singleton instance for external use
_pattern_engine = SymbolicPatternEngine()


def detect_patterns_from_logic(logic: str) -> List[Dict[str, Any]]:
    """
    Wrapper for external systems to use pattern detection on a single logic string.
    """
    glyphs = [{"text": logic, "id": "temp"}]
    return _pattern_engine.detect_patterns(glyphs)


def update_resonance_weights(coherence: float, entanglement: float) -> None:
    """
    Global update for all registered patterns' resonance-weighted SQI values.
    Used by Aion↔QQC coupling loop.
    """
    from backend.modules.patterns.pattern_registry import registry
    import time as _time

    for pattern in registry.get_all_patterns():
        base = float(pattern.sqi_score or 0.3)
        pattern.sqi_score = round(base * (1 + float(coherence) * 0.2) * (1 + float(entanglement) * 0.1), 4)
        pattern.metadata["last_resonance_update"] = {
            "coherence": coherence,
            "entanglement": entanglement,
            "updated": _time.time(),
        }
    registry.save()
    logger.info(f"[PatternEngine] Resonance weights updated for {len(registry.get_all_patterns())} patterns.")