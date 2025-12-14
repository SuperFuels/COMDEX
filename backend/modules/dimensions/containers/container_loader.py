"""
📥 UCS Container Loader
-----------------------------------------------------
Handles loading and instantiation of all container types (Hoberman, Symbolic Expansion, UCSBase, etc.)
Integrates with:
    * UCSBaseContainer for shared features (micro-grid, time dilation, gravity)
    * HobermanContainer + SymbolicExpansionContainer (legacy compatibility)
    * ucs_runtime + geometry templates (.dc.json)
    * sqi_container_registry for KG-aware symbolic registration
"""

import json
import os
from typing import Dict, Any, Union

from backend.modules.dimensions.containers.hoberman_container import HobermanContainer
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer
from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCS_TEMPLATE_DIR
from backend.modules.dna_chain.dc_handler import load_dimension
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime

# ✅ Symbolic Container Registration Hook
from backend.modules.sqi.sqi_container_registry import _registry_register

# ✅ UCS Utils - normalize input
from backend.modules.dimensions.universal_container_system.ucs_utils import normalize_container_dict

SQI_NS = "ucs://knowledge"

# ───────────────────────────────────────────────
# Env toggles (stop uvicorn reload spam / slow ingest)
# Defaults are OPT-OUT (safe): autoload OFF unless explicitly enabled.
# ───────────────────────────────────────────────

def _env_bool(name: str, default: str = "0") -> bool:
    v = os.getenv(name, default)
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

_UCS_DEBUG = _env_bool("UCS_DEBUG", "0")

# ✅ OPT-OUT DEFAULT: do NOT autoload templates unless enabled
_UCS_AUTOLOAD_TEMPLATES = _env_bool("UCS_AUTOLOAD_TEMPLATES", "0")

# ✅ OPT-OUT DEFAULT: do NOT register/ingest into SQI/KG unless enabled
_UCS_REGISTER_TO_SQI = _env_bool("UCS_REGISTER_TO_SQI", "0")

# Comma-separated exclusions (optional)
_UCS_AUTOLOAD_EXCLUDE = {
    s.strip()
    for s in str(os.getenv("UCS_AUTOLOAD_EXCLUDE", "")).split(",")
    if s.strip()
}

# ✅ Comma-separated allowlist: if set, ONLY these files load
_UCS_AUTOLOAD_ALLOW = {
    s.strip()
    for s in str(os.getenv("UCS_AUTOLOAD_ALLOW", "")).split(",")
    if s.strip()
}

# prevent repeated autoload when multiple startup hooks fire
_AUTOLOAD_DONE = False
_AUTOLOAD_CACHE: Dict[str, Any] = {}

# prevent duplicate registry calls per-process
_REGISTERED_IDS = set()

def _dprint(*a, **k):
    if _UCS_DEBUG:
        print(*a, **k)

def _is_excluded(filename: str, container_id: str = "") -> bool:
    """
    Exclusion matches:
      - exact filename: "engineering_materials.dc.json"
      - basename id-ish: "engineering_materials"
      - exact container_id if provided
    """
    fn = (filename or "").strip()
    base = fn.replace(".dc.json", "").strip()
    cid = (container_id or "").strip()

    if not _UCS_AUTOLOAD_EXCLUDE:
        return False

    return (
        fn in _UCS_AUTOLOAD_EXCLUDE
        or base in _UCS_AUTOLOAD_EXCLUDE
        or cid in _UCS_AUTOLOAD_EXCLUDE
    )

def _safe_registry_register(container_id: str, ns: str) -> None:
    """
    Idempotent + disable-able registration.
    This is the path that causes KG/SQI seeding on startup.
    """
    if not _UCS_REGISTER_TO_SQI:
        return
    if not container_id:
        return
    if container_id in _REGISTERED_IDS:
        return
    try:
        _registry_register(container_id, ns)
        _REGISTERED_IDS.add(container_id)
    except Exception as e:
        _dprint(f"⚠️ SQI registry register failed for {container_id}: {e}")


def load_container_from_json(container_json: Dict[str, Any]) -> Union[UCSBaseContainer, HobermanContainer, SymbolicExpansionContainer, Dict[str, Any]]:
    """
    Auto-detect and load containers:
        - Hoberman (legacy)
        - Symbolic Expansion (legacy)
        - UCSBaseContainer (new standard)
    """
    container_json = normalize_container_dict(container_json)

    container_type = container_json.get("container_type", "ucs_base")
    runtime_mode = container_json.get("runtime_mode", "expanded")
    container_id = container_json.get("id") or container_json.get("container_id")
    name = container_json.get("name", f"Container-{container_id or 'anon'}")

    # ✅ UCS Base Container (New Standard)
    if container_type == "ucs_base":
        geometry = container_json.get("geometry_type", "tesseract")
        container = UCSBaseContainer(
            name=name,
            geometry=geometry,
            runtime=get_ucs_runtime()
        )
        container.id = container_id or "anon"
        container.init_micro_grid()
        container.apply_time_dilation(container_json.get("properties", {}).get("time_factor", 1.0))

        if runtime_mode == "expanded":
            container.execute()

        if container.id:
            _safe_registry_register(container.id, SQI_NS)

        return container

    # ✅ Hoberman (Legacy)
    if container_type == "hoberman":
        glyphs = container_json.get("hoberman_seed", {}).get("glyphs", [])
        hob = HobermanContainer(container_id=container_id)
        hob.id = container_id or "anon"
        hob.from_glyphs(glyphs)

        if runtime_mode == "expanded":
            hob.inflate()

        if hob.id:
            _safe_registry_register(hob.id, SQI_NS)

        return hob

    # ✅ Symbolic Expansion (Legacy)
    if container_type == "symbolic_expansion":
        glyphs = container_json.get("hoberman_seed", {}).get("glyphs", [])
        sec = SymbolicExpansionContainer(container_id=container_id)
        sec.id = container_id or "anon"
        sec.load_seed(glyphs)

        if runtime_mode == "expanded":
            sec.expand()

        if sec.id:
            _safe_registry_register(sec.id, SQI_NS)

        return sec

    # ❌ Fallback (raw JSON) - register if ID exists
    fallback_id = container_json.get("id")
    if fallback_id:
        _safe_registry_register(fallback_id, SQI_NS)

    return container_json


def register_container(container_id: str, container_path: str) -> dict:
    from backend.modules.runtime.container_runtime import ContainerRuntime

    if not os.path.exists(container_path):
        raise FileNotFoundError(f"Container file not found: {container_path}")

    with open(container_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    container = load_container_from_json(raw_data)

    if hasattr(container, "id") and not getattr(container, "id", None):
        container.id = container_id

    if isinstance(container, (UCSBaseContainer, HobermanContainer, SymbolicExpansionContainer)):
        ContainerRuntime.register(container)

    _safe_registry_register(container_id, SQI_NS)
    return container


def load_container_from_file(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Container file not found: {file_path}")

    with open(file_path, "r") as f:
        container_json = json.load(f)

    return load_container_from_json(container_json)


def auto_load_all_templates():
    """
    Auto-load and instantiate all containers from the UCS templates directory.

    Defaults (OPT-OUT):
      - UCS_AUTOLOAD_TEMPLATES=0  -> disables entirely (default)
      - UCS_REGISTER_TO_SQI=0     -> no KG/SQI ingest (default)

    Optional controls:
      - UCS_AUTOLOAD_ALLOW="core.dc.json,logic_core_atom.dc.json"
      - UCS_AUTOLOAD_EXCLUDE="engineering_materials.dc.json,physics_core.dc.json"
      - UCS_DEBUG=1
    """
    global _AUTOLOAD_DONE, _AUTOLOAD_CACHE

    if _AUTOLOAD_DONE:
        return _AUTOLOAD_CACHE

    containers: Dict[str, Any] = {}

    if not _UCS_AUTOLOAD_TEMPLATES:
        _AUTOLOAD_DONE = True
        _AUTOLOAD_CACHE = containers
        _dprint("⏭️ UCS template autoload disabled (UCS_AUTOLOAD_TEMPLATES=0)")
        return containers

    if not os.path.exists(UCS_TEMPLATE_DIR):
        _AUTOLOAD_DONE = True
        _AUTOLOAD_CACHE = containers
        _dprint(f"⚠️ UCS templates folder not found: {UCS_TEMPLATE_DIR}")
        return containers

    for file in os.listdir(UCS_TEMPLATE_DIR):
        if not file.endswith(".dc.json"):
            continue

        # ✅ allowlist wins (if provided)
        if _UCS_AUTOLOAD_ALLOW and file not in _UCS_AUTOLOAD_ALLOW:
            continue

        # filename-based exclusion (secondary)
        if _is_excluded(file):
            _dprint(f"⏭️ Skipping excluded template: {file}")
            continue

        path = os.path.join(UCS_TEMPLATE_DIR, file)
        try:
            container = load_container_from_file(path)
            cid = getattr(container, "id", "") if container is not None else ""
            if _is_excluded(file, cid):
                _dprint(f"⏭️ Skipping excluded container after load: {file} (id={cid})")
                continue
            containers[getattr(container, "name", file)] = container
        except Exception as e:
            _dprint(f"❌ Failed to load container '{file}': {e}")

    _AUTOLOAD_DONE = True
    _AUTOLOAD_CACHE = containers
    return containers


def load_decrypted_container(container_id: str) -> dict:
    from backend.modules.runtime.container_runtime import ContainerRuntime
    state_manager = StateManager()
    runtime = ContainerRuntime(state_manager)

    container = load_dimension(container_id)
    state_manager.set_current_container(container)
    return runtime.get_decrypted_current_container()


def load_container_by_id(container_id: str) -> dict:
    from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
    from backend.modules.sqi.sqi_container_registry import SQI_NS

    ucs = get_ucs_runtime()

    if _UCS_DEBUG:
        available_ids = list(ucs.container_registry.keys())
        print(f"[📦] Available containers in UCS: {available_ids}")

    container = ucs.load_container(container_id)

    if not container:
        available_ids = list(ucs.container_registry.keys())
        raise ValueError(
            f"❌ Container '{container_id}' not found in UCS runtime.\n"
            f"Available: {available_ids}"
        )

    if hasattr(container, "id") and getattr(container, "id", None):
        _safe_registry_register(container.id, SQI_NS)

    return container


__all__ = [
    "load_container_from_json",
    "load_container_from_file",
    "auto_load_all_templates",
    "load_decrypted_container",
    "load_container_by_id",
    "register_container",
]