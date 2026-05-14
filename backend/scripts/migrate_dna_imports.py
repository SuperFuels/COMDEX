# 📁 File: backend/scripts/migrate_dna_imports.py

import os

OLD_FRAGMENT = "from backend.modules.dna_chain.dna_switch import DNA_SWITCH"
NEW_FRAGMENT = "from backend.modules.dna_chain.switchboard import DNA_SWITCH"

def update_file(path):
    with open(path, "r", encoding="utf-8") as f:
        contents = f.read()

    if OLD_FRAGMENT in contents:
        updated = contents.replace(OLD_FRAGMENT, NEW_FRAGMENT)
        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"✅ Updated: {path}")
        return True
    return False

def scan_and_update(root_dir):
    updated_files = 0
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(subdir, file)
                if update_file(full_path):
                    updated_files += 1
    print(f"\n🔍 Scan complete. {updated_files} file(s) updated.")

if __name__ == "__main__":
    scan_and_update("backend/modules")