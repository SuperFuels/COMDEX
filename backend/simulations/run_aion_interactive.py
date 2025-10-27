#!/usr/bin/env python3
"""
AION Interactive Simulation Console — Phase 12
───────────────────────────────────────────────
Live REPL for symbolic resonance interaction.
Loads AION memory + KG registry and allows direct resonance queries.

Usage:
    PYTHONPATH=. python backend/simulations/run_aion_interactive.py
"""

import json
import readline
from pathlib import Path
from backend.AION.resonance.resonance_engine import update_resonance, get_resonance
from backend.modules.aion.memory.store import _load as load_memory
from backend.modules.wiki_capsules.integration.kg_query_extensions import update_capsule_meta

PROMPT = "Aion> "
KG_PATH = Path("data/kg_registry.json")
MEM_PATH = Path("data/aion/memory_store.json")

def _load_json(path: Path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def list_capsules(limit=20):
    memory = _load_json(MEM_PATH)
    print(f"📚 {len(memory)} capsules loaded from AION Memory.")
    for i, (lemma, meta) in enumerate(memory.items()):
        if i >= limit: break
        e = meta.get("E")
        print(f"  • {lemma:<20}  E={e:.5f}" if e else f"  • {lemma}")

def query_resonance(term: str):
    res = get_resonance(term)
    if not res:
        print(f"⚠️ No resonance data for '{term}', attempting fresh update…")
        res = update_resonance(term)
    print(f"🌀 {term}: SQI={res.get('SQI')} ρ={res.get('ρ')} Ī={res.get('Ī')} E={res.get('E')}")
    return res

def top_energy(n=10):
    mem = _load_json(MEM_PATH)
    ranked = sorted(((k, v.get("E", 0)) for k, v in mem.items()), key=lambda x: x[1], reverse=True)
    for i, (k, e) in enumerate(ranked[:n]):
        print(f"{i+1:02d}. {k:<20} E={e:.5f}")

def main():
    print("🌐 AION Interactive Console — Phase 12")
    print("Type 'help' for commands. Ctrl-D or 'exit' to quit.\n")

    while True:
        try:
            cmd = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Exiting AION console.")
            break

        if not cmd:
            continue
        if cmd in {"exit", "quit"}:
            break
        elif cmd == "help":
            print("""
Commands:
  list [n]             → list first n capsules from memory
  res <term>           → show resonance state for a term
  top [n]              → show top-n by symbolic energy E
  reload               → reload memory and KG
  help / exit
""")
        elif cmd.startswith("list"):
            parts = cmd.split()
            n = int(parts[1]) if len(parts) > 1 else 20
            list_capsules(n)
        elif cmd.startswith("res "):
            term = cmd.split(" ", 1)[1]
            query_resonance(term)
        elif cmd.startswith("top"):
            parts = cmd.split()
            n = int(parts[1]) if len(parts) > 1 else 10
            top_energy(n)
        elif cmd == "reload":
            print("🔁 Reloaded AION memory and KG registry.")
        else:
            print(f"❓ Unknown command: {cmd}")

if __name__ == "__main__":
    main()