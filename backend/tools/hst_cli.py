# backend/tools/hst_cli.py

import argparse
import json
import os

from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
from backend.modules.symbolic.hst.hst_injection_utils import inject_hst_to_container

def load_container(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_container(container: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(container, f, indent=2)

def preview_summary(container: dict):
    tree = container.get("symbolic_tree", {})
    root = tree.get("root", {})
    nodes = tree.get("nodes", [])

    print("\n🔍 SymbolicMeaningTree Summary:")
    print(f" • Root: {root.get('label', 'N/A')}")
    print(f" • Node Count: {len(nodes)}")

    if len(nodes) > 0:
        print(f" • First 3 Nodes:")
        for node in nodes[:3]:
            print(f"   - {node.get('label')} → {node.get('glyph', {}).get('symbol')}")

def main():
    parser = argparse.ArgumentParser(description="Inject SymbolicMeaningTree into a .dc.json container.")
    parser.add_argument("container_path", type=str, help="Path to the .dc.json container")
    parser.add_argument("--output", "-o", type=str, help="Output path (default: overwrite input file)")
    parser.add_argument("--preview", "-p", action="store_true", help="Print a summary of the injected tree")
    parser.add_argument("--save", action="store_true", help="Save container after injection (default: False)")
    parser.add_argument("--replay", action="store_true", help="Trigger replay broadcast if possible")

    args = parser.parse_args()
    container_path = args.container_path
    out_path = args.output or container_path

    if not os.path.exists(container_path):
        print(f"❌ File not found: {container_path}")
        return

    print(f"📦 Loading container: {container_path}")
    container = load_container(container_path)

    print("🧠 Injecting SymbolicMeaningTree...")
    container = inject_hst_to_container(container, context={"container_path": container_path})

    if args.preview:
        preview_summary(container)

    if args.replay:
        try:
            from backend.modules.qfield.qfc_utils import build_qfc_view
            from backend.modules.qfield.qfc_bridge import send_qfc_payload

            qfc_payload = build_qfc_view(container, mode="replay")
            send_qfc_payload(qfc_payload, mode="replay")
            print("🌌 Replay broadcast triggered.")
        except Exception as e:
            print(f"⚠️ Replay broadcast failed: {e}")

    if args.save:
        print(f"💾 Saving updated container → {out_path}")
        save_container(container, out_path)
    else:
        print("⚠️ Not saving container. Use --save to persist changes.")

if __name__ == "__main__":
    main()