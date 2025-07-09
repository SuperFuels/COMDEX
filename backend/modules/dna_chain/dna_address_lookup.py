import os
import json

# Paths to mapping data
ADDRESS_BOOK_PATH = "backend/modules/dna_chain/data/dna_address_book.json"
WORLD_MAP_PATH = "backend/modules/dna_chain/data/dna_world_map.json"

# 🔌 Path registries (used for tracking known backend/frontend modules)
BACKEND_PATHS = {}
FRONTEND_PATHS = {}

# ✅ Runtime registration functions
def register_backend_path(name: str, path: str):
    abs_path = os.path.abspath(path)
    data = load_json(ADDRESS_BOOK_PATH)
    existing = data.get(name)

    # 🚫 Skip write if already registered
    if existing and existing.get("path") == abs_path:
        return

    data[name] = {"name": name, "path": abs_path}
    with open(ADDRESS_BOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    BACKEND_PATHS[name] = abs_path
    print(f"[📁] Registered backend path: {name} → {abs_path}")

def register_frontend_path(name: str, path: str):
    data = load_json(ADDRESS_BOOK_PATH)
    existing = data.get(name)

    # 🚫 Skip write if already registered
    if existing and existing.get("path") == path:
        return

    data[name] = {"name": name, "path": path}
    with open(ADDRESS_BOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    FRONTEND_PATHS[name] = path
    print(f"[🌐] Registered frontend path: {name} → {path}")

# ✅ File loading helpers
def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ✅ Lookup helpers
def get_address_by_id(entry_id, source="book"):
    data = load_json(ADDRESS_BOOK_PATH if source == "book" else WORLD_MAP_PATH)
    return data.get(entry_id)

def fuzzy_lookup(query, source="book"):
    data = load_json(ADDRESS_BOOK_PATH if source == "book" else WORLD_MAP_PATH)
    results = {}
    for key, value in data.items():
        if query.lower() in key.lower() or query.lower() in value.get("name", "").lower():
            results[key] = value
    return results

def list_all_ids(source="book"):
    data = load_json(ADDRESS_BOOK_PATH if source == "book" else WORLD_MAP_PATH)
    return list(data.keys())

# ✅ Example usage (CLI test)
if __name__ == "__main__":
    print("Available Backend Keys:", list_all_ids("book"))
    print("Available DC Rooms:", list_all_ids("world"))