import random

ops = ["⊕", "⟲", "↔", "→", "⧖"]
op_weights = [4, 2, 1, 2, 5]  # Bias

def generate_random_qglyph_tree(depth=0, max_depth=14):
    if depth >= max_depth:
        return f"X{random.randint(1, 99)}"
    op = random.choices(ops, weights=op_weights)[0]
    return {
        op: [
            generate_random_qglyph_tree(depth + 1, max_depth),
            generate_random_qglyph_tree(depth + 1, max_depth)
        ]
    }