import os
import re

# ✅ DNA Switch
from backend.modules.dna.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

def fix_imports(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace relative imports like from ..utils.auth to from utils.auth
    content_new = re.sub(r"from \.\.(\.[\w\.]*)? import", lambda m: "from " + (m.group(1)[1:] if m.group(1) else "") + " import", content)

    # Also fix relative imports like from ..models.user import X
    content_new = re.sub(r"from \.\.([\w\.]+) import", r"from \1 import", content_new)

    if content != content_new:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content_new)
        print(f"Fixed imports in {file_path}")

def main():
    for root, _, files in os.walk("backend"):
        for file in files:
            if file.endswith(".py"):
                fix_imports(os.path.join(root, file))

if __name__ == "__main__":
    main()
