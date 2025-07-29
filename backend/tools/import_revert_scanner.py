import os
import re

ROOT_DIR = "backend"

# Regex patterns to match unintended rewrites
SAFE_REVERT_PATTERNS = [
    (r"from\s+backend\.api\.aion\s+import\s+bundle_universal_container_system", "from backend.api.aion import bundle_container"),
    (r"from\s+backend\.modules\.dna_chain\.dc_handler\s+import\s+(.*)", r"from backend.modules.dna_chain.dc_handler import \1"),
    (r"from\s+backend\.modules\.state_manager\s+import\s+(.*)", r"from backend.modules.state_manager import \1"),
    (r"from\s+backend\.modules\.lean\.lean_utils\s+import\s+(.*)", r"from backend.modules.lean.lean_utils import \1"),
    (r"from\s+backend\.modules\.encryption\.glyphvault_encryptor\s+import\s+(.*)", r"from backend.modules.encryption.glyphvault_encryptor import \1"),
    (r"from\s+backend\.modules\.glyphos\.glyph_mutation_loop\s+import\s+(.*)", r"from backend.modules.glyphos.glyph_mutation_loop import \1"),
    (r"from\s+backend\.modules\.dna_chain\.teleport\s+import\s+(.*)", r"from backend.modules.dna_chain.teleport import \1"),
    (r"from\s+backend\.modules\.runtime\.container_runtime\s+import\s+(.*)", r"from backend.modules.runtime.container_runtime import \1"),
    (r"from\s+backend\.utils\.bundle_builder\s+import\s+(.*)", r"from backend.utils.bundle_builder import \1"),
    (r"from\s+backend\.modules\.glyphos\.glyph_reverse_loader\s+import\s+(.*)", r"from backend.modules.glyphos.glyph_reverse_loader import \1"),
]

def revert_unintended():
    print(f"🔄 Scanning {ROOT_DIR} for incorrect rewrites...\n")
    reverted = []

    for dirpath, _, filenames in os.walk(ROOT_DIR):
        for file in filenames:
            if file.endswith(".py"):
                filepath = os.path.join(dirpath, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                new_lines = lines[:]
                modified = False

                for i, line in enumerate(lines):
                    for pattern, replacement in SAFE_REVERT_PATTERNS:
                        if re.search(pattern, line):
                            reverted.append((filepath, i + 1, line.strip()))
                            new_lines[i] = re.sub(pattern, replacement, line)
                            modified = True

                if modified:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)

    if reverted:
        print("✅ Reverted unintended rewrites:\n")
        for filepath, line_num, line in reverted:
            print(f"{filepath}:{line_num} → {line}")
    else:
        print("✅ No unintended rewrites found.")

if __name__ == "__main__":
    revert_unintended()