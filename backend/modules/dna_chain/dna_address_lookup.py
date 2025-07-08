import json
import os

ADDRESS_BOOK_PATH = "backend/modules/dna_chain/maps/dna_address_book.json"
WORLD_MAP_PATH = "backend/modules/dna_chain/maps/dna_world_map.json"

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

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

# ✅ Example usage
if __name__ == "__main__":
    print("Available Backend Keys:", list_all_ids("book"))
    print("Available DC Rooms:", list_all_ids("world"))
