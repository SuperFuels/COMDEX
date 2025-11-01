from backend.modules.hexcore.memory_engine import MemoryEngine

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

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
    print(f"\n🌙 Dream #{i} - {label}:\n{content}\n{'-'*60}")
