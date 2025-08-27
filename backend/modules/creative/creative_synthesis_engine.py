from typing import List, Optional, Dict, Any
from uuid import uuid4
import random

from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.glyphos.glyph_executor import execute_glyph_logic
from backend.modules.symbolic.symbol_tree_generator import inject_mutation_path
from backend.modules.knowledge_graph.knowledge_graph_writer import store_generated_glyph
from backend.modules.visualization.quantum_field_canvas_api import trigger_qfc_render
from backend.modules.consciousness.prediction_engine import suggest_simplifications
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import SQIReasoningEngine
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.lean.lean_utils import is_lean_container
from backend.modules.symbolic.symbolnet_bridge import semantic_distance


class MutationOption:
    def __init__(self, description: str, mutated_glyph: Dict[str, Any], score: float):
        self.description = description
        self.mutated_glyph = mutated_glyph
        self.score = score


class FeatureSurface:
    def __init__(self, base_glyph: Dict[str, Any]):
        self.glyph = base_glyph

    def identify_mutatable_features(self) -> List[str]:
        """Return list of mutatable features for this glyph."""
        return self.glyph.get("features", [])


class CreativeSynthesisEngine:
    def __init__(self, container: Optional[Dict[str, Any]] = None):
        if container is not None:
            self.container = container
        else:
            try:
                from backend.modules.runtime.container_runtime import ContainerRuntime
                from backend.modules.runtime.state_manager import StateManager

                state_manager = StateManager()
                crt = ContainerRuntime(state_manager)
                self.container = crt.vault_manager.get_decrypted_current_container()
            except Exception as e:
                print(f"[⚠️] Failed to auto-load container: {e}")
                self.container = {"id": "unknown"}

        self.metrics = CodexMetrics()
        self.rewriter = CodexLangRewriter()
        self.sqi = SQIReasoningEngine()
        self.failed_paths = []

    def propose_mutations(self, glyph: Dict[str, Any], goal: Optional[str] = None) -> List[MutationOption]:
        features = FeatureSurface(glyph).identify_mutatable_features()
        options = []

        for feature in features:
            for alt in self._generate_feature_alternatives(feature):
                mutated = self.rewriter.mutate_feature(glyph, feature, alt)
                score = self.evaluate_mutation(mutated, goal)
                options.append(MutationOption(f"{feature} → {alt}", mutated, score))

        return sorted(options, key=lambda o: o.score, reverse=True)

    def evaluate_mutation(self, glyph: Dict[str, Any], goal: Optional[str]) -> float:
        entropy = self.metrics.entropy_level(glyph)
        goal_match = self.metrics.goal_match_score(glyph, goal) if goal else 0.5
        sqi_score = self.sqi.score_node(glyph)

        # 🔍 Semantic score via SymbolNet bridge
        semantic_score = 0.0
        if goal and glyph.get("label"):
            try:
                semantic_score = semantic_distance(glyph["label"], goal)
            except Exception as e:
                print(f"[⚠️] Semantic scoring failed: {e}")
                semantic_score = 0.0

        # Store score in metadata (optional)
        if "metadata" not in glyph:
            glyph["metadata"] = {}
        glyph["metadata"]["semantic_goal_score"] = semantic_score

        # Weighted scoring including semantic alignment
        return 0.3 * (1 - entropy) + 0.25 * goal_match + 0.25 * sqi_score + 0.2 * semantic_score

    def recursive_synthesize(self, glyph: Dict[str, Any], depth: int = 2, goal: Optional[str] = None, verbose: bool = False) -> Dict[str, Any]:
        best = glyph
        for i in range(depth):
            mutations = self.propose_mutations(best, goal)
            if not mutations:
                self.record_failed_path(best)
                if verbose:
                    print(f"[!] No viable mutations at depth {i} for glyph: {best.get('id', '?')}")
                break
            best = mutations[0].mutated_glyph
            if verbose:
                print(f"[{i+1}] Selected mutation: {mutations[0].description}")
        return best

    def record_failed_path(self, glyph: Dict[str, Any]):
        self.failed_paths.append({
            "glyph": glyph,
            "reason": "no viable mutation",
            "path_id": str(uuid4())
        })

    def trigger_qfc_visualization(self, glyph: Dict[str, Any], context: Optional[str] = None):
        if context:
            glyph["context"] = context
        glyph["label"] = "Synthesis Result"
        trigger_qfc_render(glyph)

    def inject_into_symbol_tree(self, original: Dict[str, Any], mutated: Dict[str, Any]):
        from_node_id = original.get("id") or original.get("uuid") or "unknown"

        tree = None
        if hasattr(self, "container") and self.container:
            tree = self.container.get("symbol_tree") or self.container.get("symbolic_meaning_tree")

        if tree is None:
            print("[⚠️] No symbol tree found in container. Skipping mutation path injection.")
            return

        inject_mutation_path(tree=tree, from_node_id=from_node_id, new_glyph=mutated)

    def generate_and_store(
        self,
        glyph: Dict[str, Any],
        goal: Optional[str] = None,
        max_depth: Optional[int] = None,
        visualize: bool = True,
        verbose: bool = False
    ) -> Dict[str, Any]:
        depth = max_depth if max_depth is not None else 2
        result = self.recursive_synthesize(glyph, depth=depth, goal=goal, verbose=verbose)
        self.inject_into_symbol_tree(glyph, result)

        if "containerId" not in result and "targetContainer" not in result:
            cid = self.container.get("id") if self.container else glyph.get("containerId") or "unknown"
            result["containerId"] = cid

        if visualize:
            self.trigger_qfc_visualization(result)

        store_generated_glyph(result)
        return result

    def auto_correct_contradictions(self, glyph: Dict[str, Any]) -> Dict[str, Any]:
        suggestions = suggest_simplifications(glyph)
        if suggestions:
            return suggestions[0].get("mutated_glyph", glyph)
        return glyph

    def list_failed_paths(self) -> List[Dict[str, Any]]:
        return self.failed_paths

    def _generate_feature_alternatives(self, feature: str) -> List[str]:
        alternatives = {
            "material": ["bulletproof", "transparent", "nanofiber"],
            "texture": ["smooth", "bumpy", "liquid"],
            "mode": ["hovering", "folded", "embedded"],
        }
        return alternatives.get(feature, [f"alt_{feature}_{i}" for i in range(3)])

    def run_synthesis(
        self,
        glyph: Optional[Dict[str, Any]] = None,
        goal: Optional[str] = None,
        prompt: Optional[str] = None,
        max_depth: Optional[int] = None,
        visualize: bool = True,
        verbose: bool = False
    ) -> Dict[str, Any]:
        if goal is None and prompt:
            goal = prompt

        if glyph is None:
            raise ValueError("Missing required glyph input for synthesis.")

        return self.generate_and_store(
            glyph=glyph,
            goal=goal,
            max_depth=max_depth,
            visualize=visualize,
            verbose=verbose
        )