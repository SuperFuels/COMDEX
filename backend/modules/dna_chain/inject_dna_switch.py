import os

# ✅ Consistent import path for DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# 🚨 AUTO-GENERATED DNA SWITCH EMBED BLOCK
TEMPLATE = """
# ✅ DNA Switch Registered
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# Register this file with DNA Switch
DNA_SWITCH.register(__file__)
"""

def inject_dna_switch(target_path):
    if not os.path.exists(target_path):
        print(f"❌ File not found: {target_path}")
        return False

    with open(target_path, "r", encoding="utf-8") as f:
        contents = f.read()

    if "DNA_SWITCH.register" in contents:
        print(f"✅ DNA Switch already embedded: {target_path}")
        return True

    # Prepend DNA switch embed
    updated = TEMPLATE.strip() + "\n\n" + contents

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✅ DNA Switch injected: {target_path}")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python inject_dna_switch.py <target_file.py>")
    else:
        inject_dna_switch(sys.argv[1])