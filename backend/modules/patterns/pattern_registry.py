import os
import json
import uuid
import hashlib
from typing import List, Dict, Optional, Any, Union
from difflib import SequenceMatcher
from backend.modules.sqi.sqi_scorer import compute_entropy, compute_symmetry_score
from backend.modules.visualization.glyph_to_qfc import to_qfc_payload
from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update
import asyncio

# Path to saved pattern definitions
PATTERN_DB_PATH = "backend/data/patterns/pattern_registry.json"

def stringify_glyph(glyph: Union[str, Dict[str, Any]]) -> str:
    """
    Convert glyph (either str or dict) to a canonical string representation.
    """
    if isinstance(glyph, dict):
        return glyph.get("value") or str(glyph)
    return str(glyph)


class Pattern:
    def __init__(self,
                 name: str,
                 glyphs: List[Union[str, Dict[str, Any]]],
                 pattern_type: str,
                 trigger_logic: str = "",
                 prediction: Optional[List[Union[str, Dict[str, Any]]]] = None,
                 sqi_score: Optional[float] = None,
                 source_container: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 pattern_id: Optional[str] = None):

        self.name = name
        self.glyphs = glyphs
        self.type = pattern_type
        self.trigger_logic = trigger_logic
        self.prediction = prediction or []
        self.sqi_score = sqi_score
        self.source_container = source_container
        self.metadata = metadata or {}

        self.pattern_id = pattern_id or f"pattern-{str(uuid.uuid4())[:8]}"
        self.signature = self._generate_signature()
        stringified_glyphs = [stringify_glyph(g) for g in self.glyphs]
        self.entropy = compute_entropy(stringified_glyphs)
        self.symmetry = compute_symmetry_score(stringified_glyphs)

    def _generate_signature(self) -> str:
        raw = "-".join(stringify_glyph(g) for g in self.glyphs)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "pattern_id": self.pattern_id,
            "glyphs": self.glyphs,
            "type": self.type,
            "trigger_logic": self.trigger_logic,
            "prediction": self.prediction,
            "sqi_score": self.sqi_score,
            "source_container": self.source_container,
            "metadata": self.metadata,
            "signature": self.signature,
            "entropy": self.entropy,
            "symmetry": self.symmetry,
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Pattern':
        return Pattern(
            name=data["name"],
            pattern_id=data.get("pattern_id"),
            glyphs=data["glyphs"],
            pattern_type=data["type"],
            trigger_logic=data.get("trigger_logic", ""),
            prediction=data.get("prediction", []),
            sqi_score=data.get("sqi_score"),
            source_container=data.get("source_container"),
            metadata=data.get("metadata", {})
        )


class PatternRegistry:
    def __init__(self):
        self.patterns: Dict[str, Pattern] = {}
        self.signature_index: Dict[str, Pattern] = {}
        self.entropy_glyphs = {"⧖", "⊕", "↻", "⬁", "⚛", "🧬"}
        self.load()

    def load(self):
        if os.path.exists(PATTERN_DB_PATH):
            with open(PATTERN_DB_PATH, "r") as f:
                data = json.load(f)
                for pattern_data in data:
                    pattern = Pattern.from_dict(pattern_data)
                    self.patterns[pattern.pattern_id] = pattern
                    self.signature_index[pattern.signature] = pattern

    def save(self):
        os.makedirs(os.path.dirname(PATTERN_DB_PATH), exist_ok=True)
        with open(PATTERN_DB_PATH, "w") as f:
            json.dump([p.to_dict() for p in self.patterns.values()], f, indent=2)

    def register(self, pattern: Pattern):
        self.patterns[pattern.pattern_id] = pattern
        self.signature_index[pattern.signature] = pattern
        self.save()

        # ✅ QFC broadcast after registration
        try:
            node_payload = {
                "glyph": "🧩",
                "op": "pattern_register",
                "metadata": {
                    "pattern_id": pattern.pattern_id,
                    "name": pattern.name,
                    "type": pattern.type,
                    "sqi_score": pattern.sqi_score,
                    "entropy": pattern.entropy,
                    "symmetry": pattern.symmetry,
                }
            }
            context = {
                "container_id": pattern.source_container or "unknown",
                "source_node": pattern.pattern_id,
            }
            qfc_payload = to_qfc_payload(node_payload, context)
            asyncio.create_task(broadcast_qfc_update(context["container_id"], qfc_payload))
        except Exception as e:
            print(f"[PatternRegistry→QFC] ⚠️ Failed to broadcast pattern: {e}")

    def remove(self, pattern_id: str):
        if pattern_id in self.patterns:
            signature = self.patterns[pattern_id].signature
            del self.patterns[pattern_id]
            self.signature_index.pop(signature, None)
            self.save()

    def get(self, pattern_id: str) -> Optional[Pattern]:
        return self.patterns.get(pattern_id)

    def get_by_signature(self, signature: str) -> Optional[Pattern]:
        return self.signature_index.get(signature)

    def get_all(self) -> List[Pattern]:
        return list(self.patterns.values())

    def get_all_patterns(self) -> List[Pattern]:
        """Alias used by symbolic_pattern_engine.py for clarity."""
        return self.get_all()

    def find_by_type(self, pattern_type: str) -> List[Pattern]:
        return [p for p in self.patterns.values() if p.type == pattern_type]

    def find_by_trigger(self, keyword: str) -> List[Pattern]:
        return [p for p in self.patterns.values() if keyword in p.trigger_logic]

    def find_by_glyphs(self, glyphs: List[Union[str, Dict[str, Any]]], strict: bool = False) -> List[Pattern]:
        matches = []
        glyph_set = set(stringify_glyph(g) for g in glyphs)
        for pattern in self.patterns.values():
            pattern_glyphs = set(stringify_glyph(g) for g in pattern.glyphs)
            if strict:
                if glyph_set == pattern_glyphs:
                    matches.append(pattern)
            else:
                if glyph_set.intersection(pattern_glyphs):
                    matches.append(pattern)
        return matches

    def find_similar(self, glyphs: List[Union[str, Dict[str, Any]]], threshold: float = 0.65) -> List[Pattern]:
        query_str = "".join(stringify_glyph(g) for g in glyphs)
        matches = []
        for pattern in self.patterns.values():
            candidate_str = "".join(stringify_glyph(g) for g in pattern.glyphs)
            ratio = SequenceMatcher(None, query_str, candidate_str).ratio()
            if ratio >= threshold:
                matches.append(pattern)
        return matches

    def clear(self):
        self.patterns.clear()
        self.signature_index.clear()
        self.save()


# ✅ Singleton instance export (used by test files and CodexLang)
registry = PatternRegistry()