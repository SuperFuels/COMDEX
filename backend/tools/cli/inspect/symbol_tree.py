# File: cli/inspect/symbol_tree.py

import argparse
import json
from backend.modules.symbolic.symbol_tree_generator import (
    build_tree_from_container,
    inject_mutation_path,
    score_path_with_SQI,
)

def main():
    parser = argparse.ArgumentParser(description="Inspect or mutate a SymbolicMeaningTree")
    parser.add_argument("--container-id", type=str, help="Target container ID")
    parser.add_argument("--inject-glyph", type=str, help="Inject a glyph ID into current tree path")
    parser.add_argument("--from-node", type=str, help="Inject from specific node ID")
    parser.add_argument("--export", action="store_true", help="Export tree JSON")
    args = parser.parse_args()

    if not args.container_id:
        print("❌ --container-id is required.")
        return

    tree = build_tree_from_container(args.container_id)

    if args.inject_glyph:
        if not args.from_node:
            print("❌ --from-node is required when injecting a glyph.")
            return
        inject_mutation_path(tree, args.from_node, args.inject_glyph)
        print(f"✅ Injected {args.inject_glyph} from node {args.from_node}")

    score_path_with_SQI(tree)

    if args.export:
        print(json.dumps(tree.to_dict(), indent=2))
    else:
        print(f"✅ Tree built for container {args.container_id} with {len(tree.node_index)} nodes.")

if __name__ == "__main__":
    main()