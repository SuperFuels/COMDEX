# backend/modules/glyphos/glyph_mutator.py

import json
import os
from datetime import datetime
from backend.modules.dna_chain.dc_handler import load_dimension_by_file, save_dimension_to_file
from backend.modules.dna_chain.dna_registry import register_mutation_proposal
from difflib import unified_diff

def mutate_glyph(container_path: str, coord: str, mutation: dict, reason: str):
    """Apply a mutation to a glyph at a given coordinate and log the proposal."""
    dimension = load_dimension_by_file(container_path)
    grid = dimension.get("microgrid", {})
    old = json.dumps(grid.get(coord, {}), indent=2)

    if coord not in grid:
        print(f"[❌] Glyph at {coord} not found in {container_path}")
        return False

    # Backup original file
    backup_path = container_path.replace(".json", "_OLD.json")
    if not os.path.exists(backup_path):
        with open(backup_path, "w") as f:
            json.dump(dimension, f, indent=2)

    # Apply mutation
    grid[coord].update(mutation)
    dimension["microgrid"] = grid
    save_dimension_to_file(container_path, dimension)

    new = json.dumps(grid[coord], indent=2)
    diff = "\n".join(unified_diff(old.splitlines(), new.splitlines(), lineterm=""))

    proposal = {
        "proposal_id": f"mutate_{coord}_{int(datetime.utcnow().timestamp())}",
        "file": container_path,
        "reason": reason,
        "replaced_code": old,
        "new_code": new,
        "diff": diff,
        "approved": False,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    register_mutation_proposal(proposal)
    print(f"✅ Mutation proposal logged for glyph {coord}")
    return True