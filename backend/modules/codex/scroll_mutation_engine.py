# 📁 backend/modules/codex/scroll_mutation_engine.py

from typing import List, Dict, Any
import random
import copy

SYMBOL_MUTATIONS = {
    "Memory": ["Goal", "Emotion", "Dream"],
    "Think": ["Reflect", "Plan"],
    "Store": ["Remember", "Forget"],
    "Move": ["Shift", "Redirect"],
}

def mutate_node(node: Dict[str, Any]) -> Dict[str, Any]:
    mutated = copy.deepcopy(node)
    symbol = mutated.get("symbol", "")
    value = mutated.get("value", "")
    
    # Symbol mutation
    if symbol in SYMBOL_MUTATIONS and random.random() < 0.5:
        mutated["symbol"] = random.choice(SYMBOL_MUTATIONS[symbol])

    # Value mutation (simple string tweak)
    if isinstance(value, str) and value:
        if random.random() < 0.3:
            mutated["value"] = value[::-1]  # Reverse string (example)

    # Recurse children
    children = mutated.get("children", [])
    mutated["children"] = [mutate_node(c) for c in children]

    return mutated

def mutate_scroll_tree(tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [mutate_node(node) for node in tree]