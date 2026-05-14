import os
import re

ROOT_DIR = "backend"
PATTERN = r"from\s+backend\.modules\.containers\.(\w+)_universal_container_system\s+import\s+(.*)"
REPLACEMENT = r"from backend.modules.dimensions.universal_container_system.\1 import \2"

def fix_ucs_imports(dry_run=True):
    print("🔧 Scanning for incorrect UCS imports...\n")
    fixed = []

    for dirpath, _, files in os.walk(ROOT_DIR):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(dirpath, file)
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                new_lines = lines[:]
                modified = False
                for i, line in enumerate(lines):
                    if re.search(PATTERN, line):
                        fixed.append((path, i + 1, line.strip()))
                        new_lines[i] = re.sub(PATTERN, REPLACEMENT, line)
                        modified = True

                if modified and not dry_run:
                    with open(path, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)

    if fixed:
        print(f"⚠️ Found {len(fixed)} incorrect UCS imports:\n")
        for fpath, lineno, code in fixed:
            print(f"{fpath}:{lineno}\n   ❌ {code}")
            print(f"   ✅ Rewritten to UCS path.\n")
        if not dry_run:
            print("✅ UCS imports corrected.")
    else:
        print("✅ No incorrect UCS imports found.")

if __name__ == "__main__":
    fix_ucs_imports(dry_run=True)  # Change to False to apply