import os
import re

# Root backend path
ROOT_DIR = "backend"

# Regex: Find imports that appended `_universal_container_system` incorrectly
BAD_IMPORT_PATTERN = re.compile(
    r"from\s+backend\.modules\.containers\.(\w+)_universal_container_system\s+import\s+(.*)"
)

# Correct format template
CORRECT_IMPORT_TEMPLATE = "from backend.modules.dimensions.universal_container_system.{} import {}"

def correct_ucs_imports(dry_run=True):
    print("🔧 Scanning for incorrect UCS imports...\n")
    corrections = []

    for dirpath, _, filenames in os.walk(ROOT_DIR):
        for file in filenames:
            if file.endswith(".py"):
                filepath = os.path.join(dirpath, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                new_lines = lines[:]
                modified = False

                for i, line in enumerate(lines):
                    match = BAD_IMPORT_PATTERN.search(line)
                    if match:
                        submodule, imported_symbols = match.groups()
                        fixed_line = CORRECT_IMPORT_TEMPLATE.format(submodule, imported_symbols)
                        corrections.append((filepath, i + 1, line.strip(), fixed_line))
                        new_lines[i] = fixed_line + "\n"
                        modified = True

                if modified and not dry_run:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)

    if corrections:
        print(f"⚠️ Found {len(corrections)} incorrect UCS imports:\n")
        for file, line_no, old, new in corrections:
            print(f"{file}:{line_no}\n   ❌ {old}\n   ✅ {new}\n")

        if dry_run:
            print("\n🔍 Dry run only. No changes written. Run with `dry_run=False` to apply fixes.")
        else:
            print("\n✅ Fixes applied successfully!")
    else:
        print("✅ No incorrect UCS imports found.")

if __name__ == "__main__":
    # Preview mode (no changes written)
    correct_ucs_imports(dry_run=True)

    # To auto-fix: 
    # correct_ucs_imports(dry_run=False)