import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "writable_modules.json")

with open(CONFIG_PATH, "r") as f:
    CONFIG = json.load(f)

ALLOWED_DIRS = CONFIG.get("allowed_dirs", [])
BLOCKED_FILES = CONFIG.get("blocked_files", [])

def is_safe_path(path: str) -> bool:
    norm_path = os.path.normpath(path).replace("\\", "/")

    # Check if explicitly blocked
    for blocked in BLOCKED_FILES:
        if norm_path.endswith(os.path.normpath(blocked).replace("\\", "/")):
            return False

    # Check if within allowed directories
    for allowed in ALLOWED_DIRS:
        if norm_path.startswith(os.path.normpath(allowed).replace("\\", "/")):
            return True

    return False

def assert_safe_path(path: str):
    if not is_safe_path(path):
        raise PermissionError(f"❌ Writing to '{path}' is not permitted by writable guard.")

# Alias for compatibility with dna_writer
is_write_allowed = is_safe_path