from backend.modules.hexcore.memory_engine import MemoryEngine
from rich import print
import sys

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