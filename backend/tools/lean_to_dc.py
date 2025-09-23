# backend/tools/lean_to_dc.py
"""
Thin CLI wrapper for Lean → .dc.json export, matching the whitepaper UX.
Usage examples (run from repo root where 'backend' is the top-level dir):
  PYTHONPATH=. python backend/tools/lean_to_dc.py --input examples/theorem.lean --output containers/theorem.dc.json
  python -m backend.tools.lean_to_dc --input examples/theorem.lean --output containers/theorem.dc.json
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from backend.modules.lean.lean_exporter import build_container_from_lean, CONTAINER_MAP

def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Convert a .lean file to a glyph container (.dc.json)")
    # Accept multiple flag spellings to match whitepaper + exporter
    ap.add_argument("--input", "-i", "--lean", dest="lean_file", required=True,
                    help="Path to .lean file")
    ap.add_argument("--output", "-o", "--out", dest="out_path",
                    help="Output .dc.json path (if omitted, prints to stdout)")
    ap.add_argument("--container-type", "-t",
                    choices=list(CONTAINER_MAP.keys()), default="dc",
                    help="Target container layout (default: dc)")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return ap.parse_args(argv)

def main(argv=None) -> int:
    args = parse_args(argv)

    try:
        container = build_container_from_lean(args.lean_file, args.container_type)
        if args.out_path:
            out = Path(args.out_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("w", encoding="utf-8") as f:
                json.dump(container, f, indent=2 if args.pretty else None, ensure_ascii=False)
            print(f"[✅] Wrote container → {out}")
        else:
            print(json.dumps(container, indent=2 if args.pretty else None, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"[❌] Failed to convert Lean file: {e}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())