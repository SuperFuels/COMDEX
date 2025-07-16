# backend/modules/glyphos/glyph_mutator.py

import json
import os
from datetime import datetime
from backend.modules.dna_chain.dc_handler import load_dimension_by_file, save_dimension_to_file
from backend.modules.dna_chain.dna_registry import register_mutation_proposal
from difflib import unified_diff
from typing import Optional

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

def auto_mutate_if_expired(container_path: str, coord: str, now_ms: Optional[int] = None, fallback_value: str = "rebirth"):
    """Check if glyph at coord is expired due to decay, and auto-mutate it if so."""
    dimension = load_dimension_by_file(container_path)
    grid = dimension.get("microgrid", {})

    if coord not in grid:
        return False

    glyph = grid[coord]
    decay_limit = glyph.get("decay_limit_ms")
    created_at = glyph.get("created_at")
    now = now_ms or int(datetime.utcnow().timestamp() * 1000)

    if not decay_limit or not created_at:
        return False  # No decay logic applied

    try:
        created_time = int(datetime.fromisoformat(created_at.replace("Z", "")).timestamp() * 1000)
        age = now - created_time
    except Exception as e:
        print(f"[⚠️] Could not parse created_at for {coord}: {e}")
        return False

    if age >= int(decay_limit):
        print(f"♻️ Glyph at {coord} exceeded decay limit — rewriting...")
        mutation = {
            "value": fallback_value,
            "tag": "reborn",
            "action": "reflect",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        return mutate_glyph(
            container_path,
            coord,
            mutation,
            reason="Auto-rewrite due to decay limit exceeded"
        )

    return False