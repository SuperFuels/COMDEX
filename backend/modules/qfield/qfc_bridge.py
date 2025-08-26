import argparse
import json

from backend.modules.qfield.qfc_utils import build_qfc_view

def main():
    parser = argparse.ArgumentParser(description="🧪 Preview QFC structure for a .dc.json container.")
    parser.add_argument("cid", help="Container ID or path to .dc.json file")
    parser.add_argument("--save", help="Path to save QFC view as JSON")
    parser.add_argument("--mode", default="test", help="Mode tag: live | replay | test | mutation")
    parser.add_argument("--broadcast", action="store_true", help="Send QFC view via WebSocket")

    args = parser.parse_args()

    # 📦 Load container
    try:
        if args.cid.endswith(".json"):
            with open(args.cid, "r", encoding="utf-8") as f:
                container = json.load(f)
        else:
            from backend.modules.dimensions.universal_container_system.container_loader import load_container_by_id
            container = load_container_by_id(args.cid)
    except Exception as e:
        print(f"❌ Failed to load container: {e}")
        return

    # 🌌 Generate QFC view
    try:
        qfc_payload = build_qfc_view(container, mode=args.mode)
        print(json.dumps(qfc_payload, indent=2))

        if args.save:
            with open(args.save, "w", encoding="utf-8") as out:
                json.dump(qfc_payload, out, indent=2)
            print(f"✅ Saved QFC view to {args.save}")

        if args.broadcast:
            send_qfc_payload(qfc_payload, mode=args.mode)
            print(f"📡 QFC payload broadcast via WebSocket (mode: {args.mode})")

    except Exception as e:
        print(f"❌ Failed to generate QFC view: {e}")

if __name__ == "__main__":
    main()