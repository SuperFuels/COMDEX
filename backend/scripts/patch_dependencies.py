# backend/scripts/patch_dependencies.py
import json, sys
from backend.modules.sqi.sqi_harmonics import apply_dependency_patch

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: PYTHONPATH=. python backend/scripts/patch_dependencies.py <container.json> <target_name> <dep1,dep2,...>")
        sys.exit(2)
    path, target, deps = sys.argv[1], sys.argv[2], sys.argv[3]
    deps_list = [d.strip() for d in deps.split(",") if d.strip()]
    with open(path, "r", encoding="utf-8") as f:
        c = json.load(f)
    if apply_dependency_patch(c, target, deps_list):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=2, ensure_ascii=False)
        print(f"patched '{target}' depends_on += {deps_list}")
    else:
        print(f"target '{target}' not found")
        sys.exit(1)