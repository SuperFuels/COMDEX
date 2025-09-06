import copy
import random
from typing import Any, Dict, List

# Define the list of allowed mutation operations
MUTATION_OPERATIONS = [
    "rename_node",
    "flip_operator",
    "inject_contradiction",
    "duplicate_subtree",
    "remove_leaf",
    "swap_branches",
    "change_value",
]


def mutate_symbolic_logic(tree: Dict[str, Any], max_variants: int = 3) -> List[Dict[str, Any]]:
    """
    Perform multiple symbolic mutations on a logic tree to produce creative variants.
    """
    variants = []
    for _ in range(max_variants):
        variant = copy.deepcopy(tree)
        apply_random_mutations(variant)
        variants.append(variant)
    return variants


def apply_random_mutations(node: Dict[str, Any], depth: int = 0, max_depth: int = 3):
    """
    Recursively apply mutations to a symbolic tree.
    """
    if depth > max_depth:
        return

    # Mutate current node
    if random.random() < 0.4:
        operation = random.choice(MUTATION_OPERATIONS)
        apply_mutation(node, operation)

    # Recurse into children
    for child in node.get("children", []):
        if isinstance(child, dict):
            apply_random_mutations(child, depth + 1, max_depth)


def apply_mutation(node: Dict[str, Any], operation: str):
    """
    Applies a single mutation operation to a symbolic node.
    """
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

    # Add mutation flag for visibility
    node["mutated"] = True


def flip_operator(op: str) -> str:
    """
    Returns a flipped logical operator.
    """
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