# File: backend/scripts/generate_tree3.py

import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
OUTPUT_PATH = os.path.join(ROOT_DIR, "TREE3_PROJECT.txt")
MAX_DEPTH = 3

EXCLUDE_DIRS = {
    ".git", "__pycache__", "node_modules", ".vscode", ".idea", ".next", ".venv", "dist", "build", ".pytest_cache"
}
EXCLUDE_EXTS = {
    ".log", ".pyc", ".pyo", ".env", ".db", ".sqlite", ".lock"
}

def is_excluded(name):
    if name in EXCLUDE_DIRS:
        return True
    for ext in EXCLUDE_EXTS:
        if name.endswith(ext):
            return True
    return False

def generate_tree(path, prefix="", depth=0):
    if depth > MAX_DEPTH:
        return

    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return

    entries = [e for e in entries if not is_excluded(e)]

    for index, entry in enumerate(entries):
        full_path = os.path.join(path, entry)
        is_last = index == len(entries) - 1
        branch = "└── " if is_last else "├── "
        pointer = prefix + branch

        if os.path.isdir(full_path):
            print(f"{pointer}{entry}/")
            extension = "    " if is_last else "│   "
            generate_tree(full_path, prefix + extension, depth + 1)
        else:
            print(f"{pointer}{entry}")

if __name__ == "__main__":
    from io import StringIO
    import sys

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()

    print("📦 TREE 3 – FULL CLEAN PROJECT STRUCTURE\n")
    generate_tree(ROOT_DIR)

    sys.stdout = old_stdout
    tree_output = mystdout.getvalue()

    with open(OUTPUT_PATH, "w") as f:
        f.write(tree_output)

    print(f"[✅] Tree written to {OUTPUT_PATH}")