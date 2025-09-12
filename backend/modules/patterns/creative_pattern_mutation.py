import random
import copy
from typing import List, Dict, Any, Optional

from backend.modules.patterns.pattern_registry import PatternRegistry
from backend.modules.patterns.symbolic_pattern_engine import SymbolicPatternEngine
from backend.modules.glyphwave.qwave.qwave_transfer_sender import send_qwave_transfer


class CreativePatternMutation:
    """
    Mutates symbolic glyph patterns to generate creative, divergent, or optimized variants.
    """

    def __init__(self):
        self.registry = PatternRegistry()
        self.engine = SymbolicPatternEngine()

    def mutate_pattern(self, pattern: Dict[str, Any], strategy: str = "divergent") -> Dict[str, Any]:
        """
        Create a mutated version of a given pattern using the selected strategy.
        Strategies: "divergent", "compressive", "harmonic", "random"
        """
        import asyncio
        from backend.modules.visualization.qfc_payload_utils import to_qfc_payload
        from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update

        original = copy.deepcopy(pattern)
        mutated = copy.deepcopy(pattern)
        glyphs = mutated["glyphs"]

        if strategy == "random":
            self._random_swap(glyphs)
        elif strategy == "divergent":
            self._inject_noise(glyphs)
        elif strategy == "compressive":
            self._simplify(glyphs)
        elif strategy == "harmonic":
            self._harmonize(glyphs)
        else:
            raise ValueError(f"Unknown mutation strategy: {strategy}")

        mutated["mutation_strategy"] = strategy
        mutated["parent_pattern_id"] = original.get("pattern_id")
        mutated["pattern_id"] = f"{original['pattern_id']}-mut-{random.randint(1000, 9999)}"
        mutated["sqi_score"] = self.engine.evaluate_pattern_sqi(mutated)

        # ✅ QFC WebSocket broadcast after mutation
        try:
            node_payload = {
                "glyph": "🧬",
                "op": "pattern_mutation",
                "metadata": {
                    "strategy": strategy,
                    "pattern_id": mutated["pattern_id"],
                    "parent_id": mutated.get("parent_pattern_id"),
                    "sqi_score": mutated["sqi_score"],
                    "glyph_count": len(mutated.get("glyphs", [])),
                },
            }
            context = {
                "container_id": mutated.get("container_id", "unknown"),
                "source_node": mutated.get("pattern_id", "unknown"),
            }
            qfc_payload = to_qfc_payload(node_payload, context)
            asyncio.create_task(broadcast_qfc_update(context["container_id"], qfc_payload))
        except Exception as e:
            print(f"[Pattern→QFC] ⚠️ Failed to broadcast mutated pattern: {e}")

        # ✅ QWave Transfer Broadcast
        try:
            from backend.modules.qwave.qwave_transfer_sender import send_qwave_transfer
            send_qwave_transfer(
                container_id=mutated.get("container_id", "unknown"),
                source="creative_pattern_mutation",
                beam_data=mutated
            )
        except Exception as e:
            print(f"[Pattern→QWave] ⚠️ QWave transfer failed: {e}")

        return mutated

    def _random_swap(self, glyphs: List[Any]):
        if len(glyphs) > 1:
            idx1, idx2 = random.sample(range(len(glyphs)), 2)
            glyphs[idx1], glyphs[idx2] = glyphs[idx2], glyphs[idx1]

    def _inject_noise(self, glyphs: List[Any]):
        new_glyph = self._random_glyph()
        insert_pos = random.randint(0, len(glyphs))
        glyphs.insert(insert_pos, new_glyph)

    def _simplify(self, glyphs: List[Any]):
        if len(glyphs) > 2:
            del glyphs[random.randint(0, len(glyphs) - 1)]

    def _harmonize(self, glyphs: List[Any]):
        for i, g in enumerate(glyphs):
            similar = self.registry.find_similar_glyphs(g)
            if similar:
                glyphs[i] = random.choice(similar)

    def _random_glyph(self) -> Dict[str, Any]:
        """
        Generate a random glyph for mutation purposes.
        """
        return random.choice([
            {"type": "operator", "value": "⊗"},
            {"type": "variable", "value": "x"},
            {"type": "constant", "value": 1},
            {"type": "operator", "value": "∧"},
            {"type": "operator", "value": "∨"},
        ])

    def mutate_batch(self, patterns: List[Dict[str, Any]], strategy: str = "divergent") -> List[Dict[str, Any]]:
        return [self.mutate_pattern(p, strategy) for p in patterns]

    def propose_mutations_for_container(self, container: Dict[str, Any], strategy: str = "divergent") -> List[Dict[str, Any]]:
        """
        Detect patterns in a container and propose mutated versions.
        FIXED: Pass correct glyphs to detect_patterns.
        """
        glyphs = container.get("glyphs", [])
        container_id = container.get("container_id", "unknown")

        detected_patterns = self.engine.detect_patterns(
            glyphs=glyphs,
            container_id=container_id,
            container=container
        )

        if not detected_patterns:
            print("❌ No matching patterns found for mutation.")
            return []

        return self.mutate_batch(detected_patterns, strategy=strategy)