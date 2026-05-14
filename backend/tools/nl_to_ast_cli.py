# File: backend/tools/nl_to_ast_cli.py

import argparse
import json
from backend.modules.symbolic.natural_language_parser import parse_nl_to_ast

def main():
    parser = argparse.ArgumentParser(description="Convert natural language to CodexAST.")
    parser.add_argument("input", help="Natural language input")
    parser.add_argument("--debug", action="store_true", help="Print AST details")

    args = parser.parse_args()

    try:
        ast = parse_nl_to_ast(args.input)
        print("✅ Parsed CodexAST:")
        print(f"  AST: {json.dumps(ast.to_dict(), indent=2)}")

        # ✅ Safe metadata inspection
        if args.debug:
            meta = getattr(ast, "metadata", None)
            if meta:
                print("  Metadata:", json.dumps(meta, indent=2))
            else:
                print("  No metadata found.")

    except Exception as e:
        print(f"❌ Error parsing input: {e}")

if __name__ == "__main__":
    main()