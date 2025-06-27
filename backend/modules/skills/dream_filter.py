from backend.modules.hexcore.memory_engine import MemoryEngine

def filter_dreams_by_keyword(keyword: str):
    memory = MemoryEngine()
    dreams = [m for m in memory.get_all() if m.get("label", "").startswith("dream_reflection")]

    if not dreams:
        print("🧠 No dream reflections found.")
        return

    matches = []
    for entry in dreams:
        content = entry.get("content", "")
        if keyword.lower() in content.lower():
            matches.append(content)

    if matches:
        print(f"\n🔎 Found {len(matches)} matching dream(s) for '{keyword}':\n")
        for i, m in enumerate(matches, 1):
            print(f"\n🌙 Match #{i}:\n{m}\n" + "-" * 60)
    else:
        print(f"❌ No dreams matched the keyword '{keyword}'.")

if __name__ == "__main__":
    keyword = input("🔍 Enter a keyword to search dream reflections: ")
    filter_dreams_by_keyword(keyword.strip())