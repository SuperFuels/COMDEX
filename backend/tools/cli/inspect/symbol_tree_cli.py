# File: backend/cli/inspect/symbol_tree_cli.py

import argparse
import json
import sys
from pathlib import Path

# Import the SymbolicMeaningTree system
from backend.modules.symbolic.symbol_tree_generator import (
    build_tree_from_container,
    inject_mutation_path,
    score_path_with_SQI,
)


def visualize_tree(tree, mode="ascii"):
    if mode == "ascii":
        def recurse(node, indent=0):
            prefix = "  " * indent
            print(f"{prefix}- {node.glyph_id} [{node.meaning_type}] entropy={node.entropy:.2f} goalScore={node.goal_score:.2f}")
            for child in node.children:
                recurse(child, indent + 1)

        recurse(tree.root)
    elif mode == "json":
        print(json.dumps(tree.to_dict(), indent=2))
    else:
        print("Unsupported mode. Use 'ascii' or 'json'.")


def main():
    parser = argparse.ArgumentParser(description="Inspect or modify SymbolicMeaningTree")
    parser.add_argument("--container-id", help="The container ID to load")
    parser.add_argument("--inject-glyph", help="Glyph ID to inject into mutation path")
    parser.add_argument("--score", action="store_true", help="Score the tree using SQI")
    parser.add_argument("--mode", default="ascii", help="Visualization mode: ascii | json")

    args = parser.parse_args()

    if not args.container_id:
        print("--container-id is required.")
        sys.exit(1)

    try:
        tree = build_tree_from_container(args.container_id)

        if args.inject_glyph:
            print(f"\n📥 Injecting mutation glyph: {args.inject_glyph}\n")
            inject_mutation_path(tree, args.inject_glyph)

        if args.score:
            print("\n🔎 Scoring symbolic path with SQI...\n")
            score_path_with_SQI(tree)

        print("\n🌳 Symbolic Tree Visualization:")
        visualize_tree(tree, mode=args.mode)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()