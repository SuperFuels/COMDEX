# File: backend/scripts/approve_mutation.py

import os
import json
from datetime import datetime
from backend.modules.dna_chain.dc_handler import get_dc_path, load_dc_container, save_dc_container
from backend.modules.dna_chain.dna_registry import DNA_REGISTRY_PATH
from backend.modules.hexcore.memory_engine import store_memory

def approve_and_apply():
    if not os.path.exists(DNA_REGISTRY_PATH):
        print("❌ Registry file not found.")
        return

    with open(DNA_REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    proposals = data.get("proposals", [])
    pending = [p for p in proposals if not p.get("approved")]

    if not pending:
        print("✅ No pending proposals.")
        return

    print(f"\n🧬 Pending Proposals: {len(pending)}\n")
    for i, p in enumerate(pending):
        print(f"{i+1}. {p['diff']} ({p['file']})")

    choice = input("\n🔢 Enter number to approve & apply: ")
    try:
        index = int(choice) - 1
        proposal = pending[index]
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        return

    # Apply mutation to container
    path = get_dc_path(proposal["file"].replace(".dc", ""))
    container_id = proposal["file"].replace(".dc.json", "")
    container = load_dc_container(container_id)
    coord = proposal["diff"].split(" at ")[-1].strip()
    new_data = json.loads(proposal["new_code"])

    if coord not in container.get("microgrid", {}):
        print(f"⚠️ Glyph not found at {coord} in container.")
        return

    container["microgrid"][coord] = new_data
    save_dc_container(proposal["file"].replace(".dc", ""), container)

    # Mark approved
    proposal["approved"] = True
    proposal["approved_on"] = datetime.utcnow().isoformat()

    with open(DNA_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Mutation applied and approved: {proposal['proposal_id']}")

    # ✅ Valid memory format
    store_memory({
        "label": "mutation:approved",
        "content": f"Mutation {proposal['proposal_id']} applied: {proposal['diff']} in {proposal['file']}"
    })

if __name__ == "__main__":
    approve_and_apply()