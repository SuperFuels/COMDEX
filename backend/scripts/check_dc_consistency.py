import json, sys, pathlib

def check_dc(path):
    p = pathlib.Path(path)
    data = json.loads(p.read_text())
    ids = [n["id"] for n in data.get("nodes", []) if isinstance(n, dict) and "id" in n]
    dupes = {i for i in ids if ids.count(i) > 1}
    bad_links = []
    for e in data.get("links", []):
        if e.get("src") not in ids or e.get("dst") not in ids:
            bad_links.append(e)
    print(f"✅ {p.name}: {len(ids)} nodes, {len(data.get('links', []))} links")
    if dupes:
        print("  ⚠️ duplicate node IDs:", sorted(dupes))
    if bad_links:
        print("  ❌ links with missing endpoints:")
        for e in bad_links:
            print("   -", e)
    else:
        print("  🎯 all link endpoints resolved")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_dc_consistency.py <file1.dc.json> [file2...]")
        sys.exit(1)
    for f in sys.argv[1:]:
        check_dc(f)