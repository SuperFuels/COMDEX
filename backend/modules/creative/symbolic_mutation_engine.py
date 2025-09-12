# File: backend/modules/creative/symbolic_mutation_engine.py

"""
symbolic_mutation_engine.py

Performs symbolic logic tree mutations and beam-aware variant generation.
Used by CodexExecutor, SQI Kernel, and Virtual CPU for beam path exploration.
Includes logic + beam mutation, SQI fork support, and entropy scoring hooks.
"""

import copy
import random
import logging
import uuid
from typing import Any, Dict, List

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.codex.beam_history import register_beam_mutation
from backend.modules.codex.symbolic_entropy import compute_entropy_metrics
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import SQIReasoningEngine

logger = logging.getLogger(__name__)

MUTATION_OPERATIONS = [
    "rename_node",
    "flip_operator",
    "inject_contradiction",
    "duplicate_subtree",
    "remove_leaf",
    "swap_branches",
    "change_value",
]

def mutate_beam(original_beam: WaveState, max_variants: int = 3) -> WaveState:
    """
    Generate symbolic variants of the beam’s internal logic and mutate beam metadata.
    Returns one selected mutated beam. Beam fork logic handled by fork_beam_paths().
    """
    base_tree = getattr(original_beam, "logic_tree", None)
    if not base_tree:
        logger.warning("[Mutation] Beam missing logic_tree; skipping mutation")
        return original_beam

    variants = mutate_symbolic_logic(base_tree, max_variants=max_variants)
    chosen = random.choice(variants)

    mutated_beam = copy.deepcopy(original_beam)
    mutated_beam.logic_tree = chosen
    mutated_beam.phase += random.uniform(-0.1, 0.1)
    mutated_beam.amplitude *= random.uniform(0.9, 1.1)
    mutated_beam.coherence *= random.uniform(0.95, 1.05)
    mutated_beam.origin_trace.append("mutation")
    mutated_beam.status = "mutated"
    mutated_beam.id = getattr(mutated_beam, "id", str(uuid.uuid4()))

    # Re-score SQI and recompute entropy
    sqi_engine = SQIReasoningEngine()
    mutated_beam.sqi_score = sqi_engine.score_node(mutated_beam.logic_tree)
    mutated_beam.entropy = compute_entropy_metrics(mutated_beam)

    # Register mutation in beam history
    register_beam_mutation(
        beam_id=mutated_beam.id,
        mutation={
            "type": "symbolic_mutation",
            "details": {
                "from": original_beam.logic_tree.get("label", "unknown"),
                "to": mutated_beam.logic_tree.get("label", "unknown"),
                "mutation_ops": [
                    node.get("mutation_note")
                    for node in mutated_beam.logic_tree.get("children", [])
                    if node.get("mutated")
                ]
            }
        },
        container_id=getattr(mutated_beam, "container_id", None),
        symbolic_context={
            "sqi_score": mutated_beam.sqi_score,
            "entropy": mutated_beam.entropy,
            "trace": mutated_beam.origin_trace,
            "status": mutated_beam.status
        },
        broadcast=True
    )

    # ✅ QFC Broadcast for mutated beam
    try:
        from backend.modules.visualization.glyph_to_qfc import to_qfc_payload
        from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update
        import asyncio

        node_payload = {
            "glyph": "✹",
            "op": "mutate",
            "metadata": {
                "sqi_score": mutated_beam.sqi_score,
                "entropy": mutated_beam.entropy,
                "status": mutated_beam.status,
                "mutation_ops": [
                    node.get("mutation_note")
                    for node in mutated_beam.logic_tree.get("children", [])
                    if node.get("mutated")
                ],
            }
        }

        context = {
            "container_id": getattr(mutated_beam, "container_id", "unknown"),
            "source_node": original_beam.id
        }

        qfc_payload = to_qfc_payload(node_payload, context)
        asyncio.create_task(broadcast_qfc_update(context["container_id"], qfc_payload))

        # 🌊 Emit QWave Beam for symbolic mutation
        from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam
        beam_payload = {
            "event": "symbolic_mutation",
            "glyph": "✹",
            "mutation_ops": [
                node.get("mutation_note")
                for node in mutated_beam.logic_tree.get("children", [])
                if node.get("mutated")
            ],
            "sqi_score": mutated_beam.sqi_score,
            "entropy": mutated_beam.entropy,
            "status": mutated_beam.status,
            "beam_id": mutated_beam.id
        }
        asyncio.create_task(emit_qwave_beam(
            source="symbolic_mutation",
            payload=beam_payload,
            context=context
        ))

    except Exception as qfc_err:
        print(f"[Mutation→QFC] ⚠️ Failed to stream mutation to QFC: {qfc_err}")

    return mutated_beam

def fork_beam_paths(original_beam: WaveState, forks: int = 3) -> List[WaveState]:
    """
    Create multiple mutated versions of a beam for speculative execution.
    Each variant receives symbolic + wave property mutation.
    """
    base_tree = getattr(original_beam, "logic_tree", None)
    if not base_tree:
        return [original_beam]

    logic_variants = mutate_symbolic_logic(base_tree, max_variants=forks)
    forked_beams = []

    for variant in logic_variants:
        b = copy.deepcopy(original_beam)
        b.logic_tree = variant
        b.phase += random.uniform(-0.15, 0.15)
        b.amplitude *= random.uniform(0.85, 1.15)
        b.coherence *= random.uniform(0.9, 1.1)
        b.origin_trace.append("fork")
        b.status = "forked"
        b.id = getattr(b, "id", str(uuid.uuid4()))

        sqi_engine = SQIReasoningEngine()
        b.sqi_score = sqi_engine.score_node(b.logic_tree)
        b.entropy = compute_entropy_metrics(b)

        register_beam_mutation(
            beam_id=b.id,
            mutation={
                "type": "symbolic_fork",
                "details": {
                    "from": original_beam.logic_tree.get("label", "unknown"),
                    "to": b.logic_tree.get("label", "unknown"),
                    "mutation_ops": [
                        node.get("mutation_note")
                        for node in b.logic_tree.get("children", [])
                        if node.get("mutated")
                    ]
                }
            },
            container_id=getattr(b, "container_id", None),
            symbolic_context={
                "sqi_score": b.sqi_score,
                "entropy": b.entropy,
                "trace": b.origin_trace,
                "status": b.status
            },
            broadcast=True
        )

        forked_beams.append(b)

    return forked_beams

def mutate_symbolic_logic(tree: Dict[str, Any], max_variants: int = 3) -> List[Dict[str, Any]]:
    variants = []
    for _ in range(max_variants):
        variant = copy.deepcopy(tree)
        apply_random_mutations(variant)
        variants.append(variant)
    return variants

def apply_random_mutations(node: Dict[str, Any], depth: int = 0, max_depth: int = 3):
    if depth > max_depth:
        return
    if random.random() < 0.4:
        operation = random.choice(MUTATION_OPERATIONS)
        apply_mutation(node, operation)
    for child in node.get("children", []):
        if isinstance(child, dict):
            apply_random_mutations(child, depth + 1, max_depth)

def apply_mutation(node: Dict[str, Any], operation: str):
    if operation == "rename_node":
        old_label = node.get("label", "")
        node["label"] = f"{old_label}_v{random.randint(1, 99)}"
        node["mutation_note"] = "renamed node"

    elif operation == "flip_operator":
        if "op" in node:
            node["op"] = flip_operator(node["op"])
            node["mutation_note"] = "flipped operator"

    elif operation == "inject_contradiction":
        node["contradiction"] = True
        node["label"] = f"¬({node.get('label', '')})"
        node["mutation_note"] = "injected contradiction"

    elif operation == "duplicate_subtree":
        if "children" in node and node["children"]:
            chosen = random.choice(node["children"])
            node["children"].append(copy.deepcopy(chosen))
            node["mutation_note"] = "duplicated subtree"

    elif operation == "remove_leaf":
        if "children" in node and len(node["children"]) > 1:
            node["children"].pop(random.randint(0, len(node["children"]) - 1))
            node["mutation_note"] = "removed leaf"

    elif operation == "swap_branches":
        if "children" in node and len(node["children"]) >= 2:
            random.shuffle(node["children"])
            node["mutation_note"] = "swapped branches"

    elif operation == "change_value":
        if "value" in node and isinstance(node["value"], (int, float)):
            perturb = random.uniform(-1.0, 1.0)
            node["value"] += perturb
            node["mutation_note"] = f"changed value by {perturb:.2f}"

    node["mutated"] = True

def flip_operator(op: str) -> str:
    opposites = {
        "AND": "OR",
        "OR": "AND",
        "→": "←",
        "←": "→",
        "↔": "¬↔",
        "¬↔": "↔",
        "=": "≠",
        "≠": "=",
        ">": "<",
        "<": ">",
    }
    return opposites.get(op, f"¬{op}")

class SymbolicMutationEngine:
    """
    Provides mutation utilities for symbolic logic patterns and trees.
    Supports both single mutation and variant generation.
    """

    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth

    def mutate_from_pattern(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a single symbolic mutation on the given pattern.
        """
        variants = self._mutate_symbolic_logic(pattern, max_variants=1)
        return variants[0] if variants else pattern

    def mutate_variants(self, pattern: Dict[str, Any], count: int = 3) -> List[Dict[str, Any]]:
        """
        Generate multiple symbolic mutation variants.
        """
        return self._mutate_symbolic_logic(pattern, max_variants=count)

    def _mutate_symbolic_logic(self, tree: Dict[str, Any], max_variants: int = 3) -> List[Dict[str, Any]]:
        variants = []
        for _ in range(max_variants):
            variant = copy.deepcopy(tree)
            self._apply_random_mutations(variant)
            variants.append(variant)
        return variants

    def _apply_random_mutations(self, node: Dict[str, Any], depth: int = 0):
        if depth > self.max_depth:
            return
        if random.random() < 0.4:
            operation = random.choice(MUTATION_OPERATIONS)
            self._apply_mutation(node, operation)
        for child in node.get("children", []):
            if isinstance(child, dict):
                self._apply_random_mutations(child, depth + 1)

    def _apply_mutation(self, node: Dict[str, Any], operation: str):
        if operation == "rename_node":
            old_label = node.get("label", "")
            node["label"] = f"{old_label}_v{random.randint(1, 99)}"
            node["mutation_note"] = "renamed node"

        elif operation == "flip_operator":
            if "op" in node:
                node["op"] = flip_operator(node["op"])
                node["mutation_note"] = "flipped operator"

        elif operation == "inject_contradiction":
            node["contradiction"] = True
            node["label"] = f"¬({node.get('label', '')})"
            node["mutation_note"] = "injected contradiction"

        elif operation == "duplicate_subtree":
            if "children" in node and node["children"]:
                chosen = random.choice(node["children"])
                node["children"].append(copy.deepcopy(chosen))
                node["mutation_note"] = "duplicated subtree"

        elif operation == "remove_leaf":
            if "children" in node and len(node["children"]) > 1:
                node["children"].pop(random.randint(0, len(node["children"]) - 1))
                node["mutation_note"] = "removed leaf"

        elif operation == "swap_branches":
            if "children" in node and len(node["children"]) >= 2:
                random.shuffle(node["children"])
                node["mutation_note"] = "swapped branches"

        elif operation == "change_value":
            if "value" in node and isinstance(node["value"], (int, float)):
                perturb = random.uniform(-1.0, 1.0)
                node["value"] += perturb
                node["mutation_note"] = f"changed value by {perturb:.2f}"

        node["mutated"] = True