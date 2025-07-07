from backend.modules.hexcore.memory_engine import MemoryEngine
from rich import print
import sys

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

def list_dreams(filter_keyword=None):
    memory = MemoryEngine()
    dreams = [m for m in memory.get_all() if m["label"].startswith("dream")]

    if not dreams:
        print("[yellow]⚠️ No dreams found in memory.[/yellow]")
        return

    for idx, dream in enumerate(dreams, 1):
        label = dream["label"]
        content = dream["content"]

        if filter_keyword and filter_keyword.lower() not in content.lower():
            continue

        print(f"\n[bold cyan]🌙 Dream {idx} — {label}[/bold cyan]")
        print(f"[dim]{content[:500]}...[/dim]")  # Show preview

if __name__ == "__main__":
    keyword = sys.argv[1] if len(sys.argv) > 1 else None
    list_dreams(filter_keyword=keyword)