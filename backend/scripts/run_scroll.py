# backend/scripts/run_scroll.py
import sys, json
from backend.codexcore_virtual.instruction_registry import registry

def run(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                sym, payload = line.split(" ", 1)
                data = json.loads(payload)
            except ValueError:
                print(json.dumps({"line": i, "error": "Parse error (need 'SYMBOL {json}')"}, ensure_ascii=False))
                continue
            try:
                out = registry.execute(sym, data)   # supports dict payloads
                print(json.dumps({"line": i, "symbol": sym, "out": out}, ensure_ascii=False))
            except Exception as e:
                print(json.dumps({"line": i, "symbol": sym, "error": str(e)}, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/run_scroll.py physics_demo.codex")
        sys.exit(1)
    run(sys.argv[1])