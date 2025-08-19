import argparse
import json
import requests

def main():
    parser = argparse.ArgumentParser(description="Inject symbolic glyph into AION via API.")
    parser.add_argument('--op', required=True, help='Operation name (e.g. curl, grad)')
    parser.add_argument('--args', type=str, help='JSON string of arguments')
    parser.add_argument('--codexlang', help='CodexLang expression (optional)')
    parser.add_argument('--glyph', type=str, help='JSON string of the full glyph node (optional)')
    parser.add_argument('--domain', default='general', help='Domain tag (e.g. physics.vector)')
    parser.add_argument('--source', default='cli', help='Source label (default: cli)')
    parser.add_argument('--tags', nargs='*', default=[], help='List of tags (e.g. physics quantum)')

    args = parser.parse_args()

    # Build payload
    payload = {
        "op": args.op,
        "args": json.loads(args.args) if args.args else None,
        "codexlang": args.codexlang,
        "glyph": json.loads(args.glyph) if args.glyph else None,
        "domain": args.domain,
        "source": args.source,
        "tags": args.tags
    }

    # Send to API
    try:
        res = requests.post("http://localhost:8000/symbolic/ingest", json=payload)
        print(f"[Response {res.status_code}]: {res.text}")
    except Exception as e:
        print(f"[ERROR]: {e}")

if __name__ == "__main__":
    main()