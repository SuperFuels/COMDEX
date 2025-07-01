from modules.hexcore.memory_engine import MemoryEngine

memory = MemoryEngine()
all_memories = memory.get_all()

# Match any memory with "dream" in the label
dreams = [m for m in all_memories if "dream" in m.get("label", "").lower()]

if not dreams:
    print("🧠 No dream reflections found.")
    exit()

print(f"📜 AION Dream Reflection Log ({len(dreams)} entries):\n")

for i, dream in enumerate(dreams, start=1):
    label = dream.get("label", "unknown")
    content = dream.get("content", "[No Content]")
    print(f"\n🌙 Dream #{i} — {label}:\n{content}\n{'-'*60}")
