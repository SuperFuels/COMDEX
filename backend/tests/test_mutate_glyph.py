# File: backend/tests/test_mutate_glyph.py

import uuid
import json
from datetime import datetime
from backend.modules.dna_chain.dc_handler import (
    load_dimension_by_file,
    save_dimension,
    get_dc_path
)
from backend.modules.dna_chain.dna_registry import register_proposal

GLYPH_TO_MUTATE = "✦"  # DreamCore trigger glyph
TARGET_FILE = "test_trigger"  # Filename without .dc.json suffix

def mutate_glyph_in_container():
    container_path = get_dc_path(TARGET_FILE)
    container = load_dimension_by_file(container_path)

    microgrid = container.get("microgrid", {})
    mutated = False

    for coord, meta in microgrid.items():
        if meta.get("glyph") == GLYPH_TO_MUTATE:
            old_meta = meta.copy()
            meta["glyph"] = "🧭"  # Change to teleport glyph
            meta["tag"] = "test-mutation"
            mutated = True

            proposal_id = str(uuid.uuid4())
            proposal = {
                "proposal_id": proposal_id,
                "file": f"{TARGET_FILE}.dc.json",
                "reason": "Testing glyph mutation from ✦ to 🧭",
                "replaced_code": json.dumps(old_meta, indent=2),
                "new_code": json.dumps(meta, indent=2),
                "diff": f"{GLYPH_TO_MUTATE} → 🧭 at {coord}",
                "approved": False,
                "timestamp": datetime.utcnow().isoformat()
            }

            print(f"🧬 Submitting mutation proposal: {proposal_id}")
            register_proposal(proposal)
            break

    if not mutated:
        print("❌ No matching glyph found to mutate.")
        return

    container["microgrid"] = microgrid
    save_dimension(container_path, container)
    print(f"✅ Mutation applied to container '{TARGET_FILE}' and saved.")

if __name__ == "__main__":
    mutate_glyph_in_container()