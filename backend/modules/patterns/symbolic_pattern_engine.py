import uuid
import json
import math
import logging
from typing import List, Dict, Any, Optional, Sequence, Union

from backend.modules.sqi.sqi_scorer import score_pattern_sqi
from backend.modules.glyphvault.soul_law_validator import SoulLawValidator
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.patterns.pattern_websocket_broadcast import PatternWebSocketBroadcaster
from backend.modules.patterns.pattern_qfc_bridge import PatternQFCBridge
from backend.modules.patterns.pattern_emotion_bridge import trigger_emotion_from_pattern
from backend.modules.patterns.pattern_prediction_hooks import PatternPredictionHooks
from backend.modules.patterns.pattern_utils import extract_all_glyphs
from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
from .pattern_registry import PatternRegistry, Pattern, stringify_glyph

logger = logging.getLogger(__name__)


class SymbolicPatternEngine:
    def __init__(self):
        self.registry = PatternRegistry()
        self.validator = SoulLawValidator()
        self.kg_writer = KnowledgeGraphWriter()
        self.qfc_bridge = PatternQFCBridge()
        self.broadcaster = PatternWebSocketBroadcaster()

    def detect_patterns(
        self,
        glyphs: List[Dict[str, Any]],
        container_id: str = "unknown",
        container: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Detects known patterns in a flat list of glyphs.
        Returns list of matched pattern dictionaries.
        """
        from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs

        matches: List[Dict[str, Any]] = []

        print(f"🌟 Detecting patterns in container: {container_id}")
        print("📦 Raw input glyphs:", glyphs)

        # ✅ Step 1: Preprocess symbol glyphs into tokenized glyphs
        processed_glyphs = []
        for glyph in glyphs:
            if glyph.get("type") == "symbol" and "text" in glyph:
                print(f"🧩 Expanding symbol glyph: {glyph['text']}")
                expanded = tokenize_symbol_text_to_glyphs(glyph["text"])
                print(f"    → Tokenized as: {expanded}")
                processed_glyphs.extend(expanded)
            else:
                processed_glyphs.append(glyph)

        glyphs = processed_glyphs
        print("🧠 Final preprocessed glyphs:", glyphs)

        # ✅ Step 2: Load all known patterns
        all_patterns = self.registry.get_all_patterns()
        print(f"📚 Loaded {len(all_patterns)} patterns in registry")

        for idx, pattern in enumerate(all_patterns):
            print(f"🔸 Pattern {idx+1}: {pattern.name}")
            print(f"    └─ Glyphs: {pattern.glyphs}")

        # ✅ Step 3: Attempt pattern matching
        for pattern in all_patterns:
            print(f"\n🔍 Checking pattern: {pattern.name}")
            print("🔸 Pattern glyphs:", pattern.glyphs)
            print("🔸 Target glyphs:", glyphs)

            if self._pattern_matches(pattern, glyphs):
                print(f"✅ MATCHED pattern: {pattern.name}")

                # 🔍 Compute SQI score for this pattern
                sqi = self.evaluate_pattern_sqi(pattern)
                pattern.sqi_score = sqi

                # 🧠 Convert Pattern → dict and enrich it
                pattern_dict = pattern.to_dict()
                pattern_dict["matched_in"] = container_id

                # ✅ Append to result
                matches.append(pattern_dict)

                # 🧬 Optional trace injection & hooks if full container was passed
                if container:
                    self.inject_pattern_trace(container, pattern_dict)
                    self.broadcaster.broadcast_pattern_detected(pattern)
                    self.qfc_bridge.trigger_qfc_from_pattern(pattern_dict, container)
                    trigger_emotion_from_pattern(pattern_dict, container)

                # 🔊 Broadcast prediction (even if no container passed)
                self.broadcaster.broadcast_pattern_prediction(pattern.name, glyphs)
            else:
                print(f"❌ NO MATCH: {pattern.name}")

        print(f"\n🎯 Final matched patterns: {len(matches)}")
        return matches

    def _pattern_matches(self, pattern: Pattern, glyphs: List[Any]) -> bool:
        """
        Check if the container glyphs include the pattern glyphs in exact order.
        """
        glyph_str_sequence = [stringify_glyph(g) for g in glyphs]
        pattern_str_sequence = [stringify_glyph(g) for g in pattern.glyphs]

        if len(glyph_str_sequence) < len(pattern_str_sequence):
            return False

        for i in range(len(glyph_str_sequence) - len(pattern_str_sequence) + 1):
            if glyph_str_sequence[i:i + len(pattern_str_sequence)] == pattern_str_sequence:
                return True

        return False

    def suggest_missing_glyphs(self, container: Dict[str, Any]) -> List[str]:
        """
        Given a container, suggest glyphs that complete or stabilize known patterns.
        """
        glyphs = extract_all_glyphs(container.get("symbolic_tree", {}))
        glyphs_str = [stringify_glyph(g) for g in glyphs]
        suggestions = []
        for pattern in self.registry.get_all_patterns():
            pattern_strs = [stringify_glyph(g) for g in pattern.glyphs]
            if 0 < sum(p in glyphs_str for p in pattern_strs) < len(pattern_strs):
                for p in pattern_strs:
                    if p not in glyphs_str:
                        suggestions.append(p)
        return list(set(suggestions))

    def mutate_pattern(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a mutated version of a pattern using symbolic mutation logic.
        """
        mutated_glyphs = self._shuffle_glyphs(pattern["glyphs"])
        mutated_pattern = Pattern(
            name=pattern["name"] + "_mutated",
            glyphs=mutated_glyphs,
            pattern_type=pattern["type"],
            trigger_logic=pattern.get("trigger_logic", ""),
            source_container=pattern.get("source_container"),
            metadata={"mutation_origin": pattern["pattern_id"]},
        )
        mutated_pattern.sqi_score = self.evaluate_pattern_sqi(mutated_pattern)
        return mutated_pattern.to_dict()

    def _shuffle_glyphs(self, glyphs: Sequence[Any]) -> List[Any]:
        from random import shuffle
        new_glyphs = list(glyphs)
        shuffle(new_glyphs)
        return new_glyphs

    def evaluate_pattern_sqi(self, pattern: Union[Pattern, Dict[str, Any]]) -> float:
        if hasattr(pattern, "to_dict"):
            return score_pattern_sqi(pattern.to_dict())
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
        self.kg_writer.inject_pattern(container_id=container.get("container_id"), pattern_trace=trace)

    def replay_pattern_trace(self, container: Dict[str, Any], pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and return a previously detected pattern trace.
        """
        for pattern in container.get("patterns", []):
            if pattern["pattern_id"] == pattern_id:
                return pattern
        return None

    def register_new_pattern(self, glyphs: List[Any], name: str, pattern_type: str, trigger_logic: str, source_container: str) -> Dict[str, Any]:
        """
        Save a new symbolic pattern to the registry.
        """
        new_pattern = Pattern(
            name=name,
            glyphs=glyphs,
            pattern_type=pattern_type,
            trigger_logic=trigger_logic,
            source_container=source_container,
        )
        new_pattern.sqi_score = self.evaluate_pattern_sqi(new_pattern)
        self.registry.register(new_pattern)
        return new_pattern.to_dict()

    def validate_pattern_ethics(self, pattern: Dict[str, Any]) -> bool:
        """
        Uses SoulLaw to verify the pattern doesn't violate ethical constraints.
        """
        return self.validator.validate_beam_event(pattern)

    def export_patterns(self) -> str:
        """
        Export all known patterns in JSON for review or training.
        """
        return json.dumps([p.to_dict() for p in self.registry.get_all_patterns()], indent=2)

# Singleton instance for external use
_pattern_engine = SymbolicPatternEngine()

def detect_patterns_from_logic(logic: str) -> List[Dict[str, Any]]:
    """
    🔍 Wrapper for external systems to use pattern detection on a single logic string.
    This wraps the full engine using dummy glyphs.
    """
    glyphs = [{"text": logic, "id": "temp"}]
    return _pattern_engine.detect_patterns(glyphs)