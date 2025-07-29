import os
import re

# Root directory of your backend codebase
ROOT_DIR = "backend"

# Regex patterns for legacy imports
IMPORT_PATTERNS = [
    (r"from\s+([\w\.]*)containers?\s+import\s+(.*)", r"from \1universal_container_system import \2"),
    (r"import\s+([\w\.]*)containers?\b", r"import \1universal_container_system")
]

EXCLUDE_DIRS = ["venv", "site-packages", "__pycache__", ".git"]

def scan_and_fix(auto_fix=False):
    print(f"🔍 Scanning {ROOT_DIR} for legacy 'container(s)' imports...\n")
    matches_found = []

    for dirpath, _, filenames in os.walk(ROOT_DIR):
        # Skip excluded directories
        if any(excluded in dirpath for excluded in EXCLUDE_DIRS):
            continue

        for file in filenames:
            if file.endswith(".py"):
                filepath = os.path.join(dirpath, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                new_lines = lines[:]
                modified = False

                for i, line in enumerate(lines):
                    for pattern, replacement in IMPORT_PATTERNS:
                        if re.search(pattern, line):
                            matches_found.append((filepath, i + 1, line.strip()))
                            if auto_fix:
                                new_lines[i] = re.sub(pattern, replacement, line)
                                modified = True

                if auto_fix and modified:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)

    if matches_found:
        print("⚠️ Legacy imports found:\n")
        for filepath, line_number, code_line in matches_found:
            print(f"{filepath}:{line_number} → {code_line}")

        if auto_fix:
            print("\n✅ Auto-fix applied: All imports rewritten to 'universal_container_system'.")
    else:
        print("✅ No legacy imports found.")

if __name__ == "__main__":
    # Preview mode (scan only)
    scan_and_fix(auto_fix=False)
    # To auto-fix, run manually: scan_and_fix(auto_fix=True)