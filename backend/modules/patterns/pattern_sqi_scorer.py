import math
import asyncio
from typing import Dict, List, Optional
from statistics import mean

from .symbolic_pattern_engine import SymbolicPattern
from .pattern_registry import PatternRegistry
from backend.modules.sqi.sqi_scorer import compute_entropy, compute_symmetry_score
from backend.modules.patterns.pattern_kg_bridge import get_kg_motif_similarity
from backend.modules.sqi.sqi_prediction_adapter import score_prediction_alignment
from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam


class PatternSQIScorer:
    """
    Computes Symbolic Quantum Intelligence (SQI) scores for symbolic glyph patterns.
    Scores reflect harmony, resonance, entropy, compression, mutation stability,
    symmetry, and prediction alignment.
    """

    def __init__(self):
        self.registry = PatternRegistry()

    def score_pattern(self, pattern: Dict) -> Dict[str, float]:
        """
        Evaluate and return a detailed SQI score dictionary for a pattern.
        """
        glyphs = pattern.get("glyphs", [])
        if not glyphs:
            return {"sqi_score": 0.0}

        score_components = {
            "length_penalty": self._length_penalty(glyphs),
            "entropy_balance": self._entropy_balance(glyphs),
            "entropy": self._entropy_score(glyphs),
            "symmetry": self._symmetry_score(glyphs),
            "resonance": self._resonance_score(glyphs),
            "resonance_kg": self._resonance_kg(pattern),
            "prediction_alignment": self._prediction_alignment(pattern),
            "mutation_stability": self._mutation_stability(pattern),
            "harmonic_coherence": self._harmonic_coherence(pattern),
            "compression": self._compression_score(glyphs),
        }

        weights = {
            "length_penalty": 0.05,
            "entropy_balance": 0.10,
            "entropy": 0.10,
            "symmetry": 0.10,
            "resonance": 0.10,
            "resonance_kg": 0.15,
            "prediction_alignment": 0.15,
            "mutation_stability": 0.10,
            "harmonic_coherence": 0.10,
            "compression": 0.05,
        }

        total_sqi = sum(score_components[k] * weights[k] for k in weights)
        score_components["sqi_score"] = round(total_sqi, 4)
        return score_components

    def _length_penalty(self, glyphs: List[str]) -> float:
        ideal_length = 3.5
        deviation = abs(len(glyphs) - ideal_length)
        return max(0.0, 1.0 - (deviation / 5.0))

    def _entropy_balance(self, glyphs: List[str]) -> float:
        entropic = [g for g in glyphs if g in self.registry.entropy_glyphs]
        return min(1.0, len(entropic) / max(len(glyphs), 1))

    def _entropy_score(self, glyphs: List[str]) -> float:
        return compute_entropy(glyphs)

    def _symmetry_score(self, glyphs: List[str]) -> float:
        return 0.0 if len(glyphs) <= 1 else compute_symmetry_score(glyphs)

    def _resonance_score(self, glyphs: List[str]) -> float:
        known_patterns = self.registry.get_all_patterns()
        if not known_patterns:
            return 0.5
        known_glyphs = [g for p in known_patterns for g in p.glyphs]
        matches = sum(1 for g in glyphs if g in known_glyphs)
        return matches / max(len(glyphs), 1)

    def _resonance_kg(self, pattern: Dict) -> float:
        try:
            return get_kg_motif_similarity(pattern)
        except Exception:
            return 0.5

    def _prediction_alignment(self, pattern: Dict) -> float:
        try:
            return score_prediction_alignment(pattern)
        except Exception:
            return 0.5

    def _mutation_stability(self, pattern: Dict) -> float:
        trace = pattern.get("mutation_trace", [])
        if not trace:
            return 0.8
        collapses = sum(1 for e in trace if "collapse" in e.get("tags", []))
        return 1.0 - (collapses / len(trace)) if len(trace) > 0 else 0.8

    def _harmonic_coherence(self, pattern: Dict) -> float:
        context = pattern.get("harmonic_context", [])
        if not context:
            return 0.5
        matches = sum(1 for p in context if p.get("signature") == pattern.get("signature"))
        return matches / len(context) if context else 0.5

    def _compression_score(self, glyphs: List[str]) -> float:
        total = len(glyphs)
        unique = len(set(glyphs))
        return 0.0 if total == 0 else 1.0 - (unique / total)

    async def attach_sqi_score(self, pattern: Dict, context: Optional[Dict] = None) -> Dict:
        """
        Mutates the pattern dictionary in-place by adding 'sqi_score'.
        Emits a QWave beam if score is above threshold.
        """
        scores = self.score_pattern(pattern)
        pattern.update(scores)

        if scores.get("sqi_score", 0.0) > 0.85:
            await emit_qwave_beam(
                source="pattern_sqi_scorer",
                payload={
                    "event": "high_sqi_pattern",
                    "pattern_signature": pattern.get("signature"),
                    "glyphs": pattern.get("glyphs"),
                    "sqi_score": scores["sqi_score"],
                    "tags": ["pattern", "sqi_spike", "symbolic_resonance"],
                    "container_id": (context or {}).get("container_id"),
                },
                context=context or {},
            )

        return pattern

    async def score_all_patterns(self, patterns: List[Dict], context: Optional[Dict] = None) -> List[Dict]:
        """
        Batch process a list of patterns and append SQI scores to each.
        Emits QWave beams for high-SQI patterns.
        """
        return await asyncio.gather(*[
            self.attach_sqi_score(p, context=context) for p in patterns
        ])


# Singleton instance
pattern_sqi_scorer = PatternSQIScorer()