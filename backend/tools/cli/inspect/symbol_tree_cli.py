import argparse
import json
import sys
import os
from pathlib import Path
from rich import print

# Symbolic Tree Core
from backend.modules.symbolic.symbol_tree_generator import (  
    build_symbolic_tree_from_container,
    inject_mutation_path,
    score_path_with_SQI,
)

# Glyph Construction
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph
from backend.modules.codex.symbolic_registry import symbolic_registry
from backend.modules.dimensions.containers.container_loader import load_container_from_file


def build_tree_from_container(container_id_or_path, inject_trace=False):
    """
    Resolve container from ID or .dc.json file path, then build symbolic meaning tree.
    """
    if os.path.exists(container_id_or_path) and container_id_or_path.endswith(".dc.json"):
        container = load_container_from_file(container_id_or_path)
    else:
        raise ValueError(f"Unsupported container ID or path: {container_id_or_path}")

    return build_symbolic_tree_from_container(container, inject_trace=inject_trace)


def visualize_tree(tree, mode="ascii"):
    def recurse(node, indent=0):
        prefix = "  " * indent
        glyph_dict = node.glyph.to_dict()
        glyph_id = glyph_dict.get("id", node.id)
        meaning_type = glyph_dict.get("meaning_type", "unknown")
        entropy = glyph_dict.get("entropy", 0.0)
        goal_score = node.goal_score or 0.0
        print(f"{prefix}- {glyph_id} [{meaning_type}] entropy={entropy:.2f} goalScore={goal_score:.2f}")
        for child in node.children:
            recurse(child, indent + 1)

    if mode == "ascii":
        recurse(tree.root)
    elif mode == "json":
        print(json.dumps(tree.to_dict(), indent=2))
    else:
        print("❌ Unsupported visualization mode. Use 'ascii' or 'json'.")


def print_replay_paths(container):
    """
    If trace → replayPaths exist, print a summary of replay trails.
    """
    trace = container.get("trace", {})
    replay_paths = trace.get("replayPaths", [])
    if not replay_paths:
        print("\nℹ️ No replay paths found in trace.")
        return

    print(f"\n📽️ [bold]Replay Paths Found:[/bold] {len(replay_paths)} total")
    for i, path in enumerate(replay_paths):
        path_str = " → ".join(path)
        print(f"  [{i+1}] {path_str}")


def main():
    parser = argparse.ArgumentParser(description="Inspect or modify a SymbolicMeaningTree")
    parser.add_argument("--container-id", help="The container ID or path (.dc.json) to load")
    parser.add_argument("--inject-glyph", help="Symbolic glyph name or ID to inject as mutation")
    parser.add_argument("--inject-from", help="Node ID to mutate from (default: root)", default=None)
    parser.add_argument("--inject-trace", action="store_true", help="Inject replay trace paths into container")
    parser.add_argument("--score", action="store_true", help="Score the tree using SQI")
    parser.add_argument("--mode", default="ascii", help="Visualization mode: ascii | json")

    args = parser.parse_args()

    if not args.container_id:
        print("❌ --container-id is required.")
        sys.exit(1)

    try:
        # 🧠 Build tree from container (with optional trace injection)
        tree = build_tree_from_container(args.container_id, inject_trace=args.inject_trace)
        print(f"\n[✅] Built tree with {len(tree.node_index)} nodes.")

        # 🔁 Inject a mutation glyph if provided
        if args.inject_glyph:
            print(f"\n📥 Injecting mutation glyph: {args.inject_glyph}")
            glyph_obj = symbolic_registry.get(args.inject_glyph)
            if not glyph_obj:
                raise ValueError(f"Unknown glyph '{args.inject_glyph}' in symbolic_registry.")
            from_node_id = args.inject_from or tree.root.id
            inject_mutation_path(tree, from_node_id, glyph_obj)

        # 🔎 Score the path using SQI
        if args.score:
            print("\n🔬 Scoring symbolic path with SQI...\n")
            score_path_with_SQI(tree)

        # 📽️ Show replay trace if requested
        if args.inject_trace:
            print_replay_paths(tree.container)

        # 🌳 Visualize final tree
        print("\n🌳 Symbolic Tree Visualization:\n")
        visualize_tree(tree, mode=args.mode)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()