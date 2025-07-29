# File: backend/modules/lean/lean_exporter.py

import sys
import json
from backend.modules.lean.lean_to_glyph import lean_to_dc_universal_container_system

def main():
    if len(sys.argv) < 2:
        print("Usage: python lean_exporter.py <path_to_lean_file>")
        sys.exit(1)

    path = sys.argv[1]

    try:
        container = lean_to_dc_container(path)
        print(json.dumps(container, indent=2))
    except Exception as e:
        print(f"[❌] Failed to convert Lean file: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()