import os
import json
from typing import Dict, Any, Optional, List, Tuple
from json import JSONDecodeError
import tempfile

# === Paths ===
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

ADDRESS_BOOK_PATH = os.path.join(DATA_DIR, "dna_address_book.json")        # legacy path book (keep)
WORLD_MAP_PATH   = os.path.join(DATA_DIR, "dna_world_map.json")            # legacy world map (keep)

# NEW: canonical registries used by UCS + teleport
CONTAINER_REGISTRY_PATH = os.path.join(DATA_DIR, "container_registry.json")  # { container_id: {address, meta, ...} }
WORMHOLE_REGISTRY_PATH  = os.path.join(DATA_DIR, "wormhole_registry.json")   # { "from->to": {from, to, meta...} }

# ───────────────────────────── Helpers ─────────────────────────────

def _ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

def _load_json(path: str) -> Dict[str, Any]:
    """
    Safe JSON load. Returns {} if the file is missing.
    Raises a clear error on malformed JSON.
    """
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"Root of {path} must be a JSON object, got {type(data).__name__}")
    return data

def _write_json(path: str, data: Dict[str, Any]) -> None:
    """
    Atomic write to avoid partial/corrupt files.
    """
    _ensure_dirs()
    d = os.path.dirname(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=d, delete=False) as tmp:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)

def _route_key(src: str, dst: str) -> str:
    return f"{src}->{dst}"

def _norm_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    return value.strip() or None

def _norm_addr(addr: Optional[str]) -> Optional[str]:
    # basic cleanup; real validation left to callers
    if addr is None:
        return None
    if not isinstance(addr, str):
        addr = str(addr)
    addr = addr.strip()
    return addr or None

# ─────────────────────────── Back-compat API ───────────────────────────
# (Keep your existing lightweight helpers so nothing else breaks)

BACKEND_PATHS: Dict[str, str] = {}
FRONTEND_PATHS: Dict[str, str] = {}

def register_backend_path(name: str, path: str):
    abs_path = os.path.abspath(path)
    data = _load_json(ADDRESS_BOOK_PATH)
    existing = data.get(name)
    if existing and existing.get("path") == abs_path:
        return
    data[name] = {"name": name, "path": abs_path}
    _write_json(ADDRESS_BOOK_PATH, data)
    BACKEND_PATHS[name] = abs_path
    print(f"[📁] Registered backend path: {name} -> {abs_path}")

def register_frontend_path(name: str, path: str):
    data = _load_json(ADDRESS_BOOK_PATH)
    existing = data.get(name)
    if existing and existing.get("path") == path:
        return
    data[name] = {"name": name, "path": path}
    _write_json(ADDRESS_BOOK_PATH, data)
    FRONTEND_PATHS[name] = path
    print(f"[🌐] Registered frontend path: {name} -> {path}")

def load_json(path):  # kept for legacy imports
    return _load_json(path)

def get_address_by_id(entry_id, source="book"):
    data = _load_json(ADDRESS_BOOK_PATH if source == "book" else WORLD_MAP_PATH)
    return data.get(entry_id)

def fuzzy_lookup(query, source="book"):
    data = _load_json(ADDRESS_BOOK_PATH if source == "book" else WORLD_MAP_PATH)
    q = (query or "").lower()
    results = {}
    for key, value in data.items():
        name = (value.get("name", "") if isinstance(value, dict) else "")
        if q in key.lower() or q in name.lower():
            results[key] = value
    return results

def list_all_ids(source="book"):
    data = _load_json(ADDRESS_BOOK_PATH if source == "book" else WORLD_MAP_PATH)
    return list(data.keys())

# ───────────────────── NEW: Universal Container Registry ─────────────────────

def register_container_address(
    container_id: str,
    address: Optional[str],
    meta: Optional[Dict[str, Any]] = None,
    kind: str = "container",
) -> Dict[str, Any]:
    """
    Idempotently registers/updates a container in the global registry.
    Stores: { container_id: { address, kind, meta } }
    """
    cid = _norm_id(container_id)
    if not cid:
        raise ValueError("container_id is required")

    addr = _norm_addr(address)
    k = _norm_id(kind) or "container"

    reg = _load_json(CONTAINER_REGISTRY_PATH)
    entry = reg.get(cid, {})
    if addr is not None:
        entry["address"] = addr
    if k is not None:
        entry["kind"] = k
    entry["meta"] = (meta or {}) if meta is not None else entry.get("meta", {})
    reg[cid] = entry

    _write_json(CONTAINER_REGISTRY_PATH, reg)
    if addr:
        print(f"[🔗] Registry: {cid} ↔ {addr}")
    else:
        print(f"[🔗] Registry: {cid} (no address)")
    return entry

def unregister_container(container_id: str) -> bool:
    """
    Removes a container from the registry and auto-unlinks its wormholes.
    """
    cid = _norm_id(container_id)
    if not cid:
        return False

    reg = _load_json(CONTAINER_REGISTRY_PATH)
    if cid not in reg:
        return False
    del reg[cid]
    _write_json(CONTAINER_REGISTRY_PATH, reg)

    # remove all wormholes where it is src or dst
    links = _load_json(WORMHOLE_REGISTRY_PATH)
    to_delete = [k for k, v in links.items() if v.get("from") == cid or v.get("to") == cid]
    for k in to_delete:
        del links[k]
    if to_delete:
        _write_json(WORMHOLE_REGISTRY_PATH, links)
        print(f"[🗑️] Unlinked {len(to_delete)} wormholes for {cid}")
    print(f"[🗑️] Unregistered container: {cid}")
    return True

def resolve_by_address(address: str) -> Optional[str]:
    """
    Returns container_id for a given ucs:// address (linear scan for now).
    """
    addr = _norm_addr(address)
    if not addr:
        return None
    reg = _load_json(CONTAINER_REGISTRY_PATH)
    for cid, entry in reg.items():
        if entry.get("address") == addr:
            return cid
    return None

def get_container_entry(container_id: str) -> Optional[Dict[str, Any]]:
    cid = _norm_id(container_id)
    if not cid:
        return None
    reg = _load_json(CONTAINER_REGISTRY_PATH)
    return reg.get(cid)

def list_registry() -> Dict[str, Any]:
    return _load_json(CONTAINER_REGISTRY_PATH)

def list_addresses() -> List[str]:
    """
    Returns a flat list of registered addresses: ["ucs://...#...", ...]
    (Kept simple because callers like UCS debug expect just addresses.)
    """
    reg = _load_json(CONTAINER_REGISTRY_PATH)
    out: List[str] = []
    for entry in reg.values():
        addr = entry.get("address")
        if addr:
            out.append(addr)
    return out

def list_address_pairs() -> List[Tuple[str, str]]:
    """
    Optional: returns [(container_id, address), ...] for callers that want both.
    """
    reg = _load_json(CONTAINER_REGISTRY_PATH)
    out: List[Tuple[str, str]] = []
    for cid, entry in reg.items():
        addr = entry.get("address")
        if addr:
            out.append((cid, addr))
    return out

# ───────────────────────── Wormhole Registry (global) ─────────────────────────

def link_wormhole(src_id: str, dst_id: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Idempotently link src -> dst in the global wormhole registry.
    """
    src = _norm_id(src_id)
    dst = _norm_id(dst_id)
    if not src or not dst:
        raise ValueError("src_id and dst_id are required")

    links = _load_json(WORMHOLE_REGISTRY_PATH)
    key = _route_key(src, dst)
    if key in links:
        if meta:
            links[key].setdefault("meta", {}).update(meta)
    else:
        links[key] = {"from": src, "to": dst, "meta": meta or {}}
    _write_json(WORMHOLE_REGISTRY_PATH, links)
    print(f"[🕳️] Wormhole linked: {src} -> {dst}")
    return links[key]

def unlink_wormhole(src_id: str, dst_id: str) -> bool:
    src = _norm_id(src_id)
    dst = _norm_id(dst_id)
    if not src or not dst:
        return False
    links = _load_json(WORMHOLE_REGISTRY_PATH)
    key = _route_key(src, dst)
    if key not in links:
        return False
    del links[key]
    _write_json(WORMHOLE_REGISTRY_PATH, links)
    print(f"[🕳️] Wormhole unlinked: {src} -> {dst}")
    return True

def list_wormholes() -> Dict[str, Any]:
    return _load_json(WORMHOLE_REGISTRY_PATH)

def find_wormhole_targets(src_id: str) -> List[str]:
    src = _norm_id(src_id)
    if not src:
        return []
    links = _load_json(WORMHOLE_REGISTRY_PATH)
    return [v["to"] for v in links.values() if v.get("from") == src]

def find_wormhole_sources(dst_id: str) -> List[str]:
    dst = _norm_id(dst_id)
    if not dst:
        return []
    links = _load_json(WORMHOLE_REGISTRY_PATH)
    return [v["from"] for v in links.values() if v.get("to") == dst]

# ─────────────────────────── CLI smoke test ───────────────────────────
if __name__ == "__main__":
    _ensure_dirs()
    print("Container registry size:", len(list_registry()))
    print("Addresses:", list_addresses())
    print("Wormholes:", len(list_wormholes()))