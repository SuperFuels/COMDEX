import os
import re

def fix_route_imports(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Replace from ..schemas.xxx import ...  -> from schemas.xxx import ...
    content = re.sub(r"from \.\.schemas(\.[\w\.]*) import", r"from schemas\1 import", content)

    # Replace from ..utils.xxx import ...     -> from utils.xxx import ...
    content = re.sub(r"from \.\.utils(\.[\w\.]*) import", r"from utils\1 import", content)

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed imports in {file_path}")

def main():
    routes_dir = os.path.join("backend", "routes")
    for root, _, files in os.walk(routes_dir):
        for file in files:
            if file.endswith(".py"):
                fix_route_imports(os.path.join(root, file))

if __name__ == "__main__":
    main()
