import random
from backend.tests.glyphos_wirepack_v24_phase_tag_bloat_balanced_benchmark import (
    Tree,
    count_nodes,
    make_balanced,
    make_chain,
    to_native_ast,
    to_tagged_ast,
)


def random_tree(n_leaves: int, seed: int) -> Tree:
    rng = random.Random(seed)
    nodes = [Tree(kind="leaf", value=i) for i in range(n_leaves)]
    while len(nodes) > 1:
        a = nodes.pop(rng.randrange(len(nodes)))
        b = nodes.pop(rng.randrange(len(nodes)))
        nodes.append(Tree(kind="node", left=a, right=b))
    return nodes[0]


def count_tag_wrappers(ast) -> int:
    """Count how many {"op":"tag",...} wrappers exist in tagged AST."""
    if isinstance(ast, dict):
        op = ast.get("op")
        if op == "tag":
            return 1 + count_tag_wrappers(ast.get("child"))
        if op == "interf":
            return count_tag_wrappers(ast.get("a")) + count_tag_wrappers(ast.get("b"))
        return 0
    return 0


def test_chain_and_balanced_generate():
    assert count_nodes(make_chain(1)) == 1
    assert count_nodes(make_chain(8)) == 15  # 8 leaves => 7 internal => 15 nodes
    assert count_nodes(make_balanced(8)) == 15


def test_one_tag_per_internal_node_bound_random():
    # Model: exactly one tag wrapper per internal node.
    # internal_nodes <= nodes - 1, so nodes + tag_wrappers <= 2*nodes.
    for n_leaves in [2, 3, 4, 8, 16, 32]:
        for seed in range(20):
            t = random_tree(n_leaves, seed)
            nodes = count_nodes(t)

            tagged = to_tagged_ast(t)
            tag_wrappers = count_tag_wrappers(tagged)

            assert tag_wrappers <= nodes - 1
            assert (nodes + tag_wrappers) <= 2 * nodes


def test_native_vs_tagged_ast_shapes():
    t = make_balanced(16)
    native = to_native_ast(t)
    tagged = to_tagged_ast(t)
    assert native["op"] == "interf"
    assert tagged["op"] == "tag"