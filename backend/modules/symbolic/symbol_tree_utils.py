# backend/modules/symbolic/symbol_tree_utils.py

import os
from typing import Any

def safe_load_container_by_id(container_id_or_path: str) -> Any:
    """
    Safe container loader using UCSRuntime (preferred), with fallback warning.
    Works for both file paths (ending in .dc.json) and registered container IDs.
    """
    from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
    ucs_runtime = get_ucs_runtime()

    # 🛠 Normalize path properly
    if container_id_or_path.endswith(".dc.json") or os.path.isfile(container_id_or_path):
        path = os.path.normpath(container_id_or_path)
        container_id = os.path.basename(path).replace(".dc.json", "")
        ucs_runtime.load_container(path)
    else:
        container_id = container_id_or_path
        ucs_runtime.load_container(container_id)

    return ucs_runtime.get_container(container_id)