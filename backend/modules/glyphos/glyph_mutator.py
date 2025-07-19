# backend/modules/glyphos/glyph_mutator.py

import json
import os
import hashlib
from datetime import datetime
from typing import Optional, Dict
from difflib import unified_diff

from backend.modules.dna_chain.dc_handler import load_dimension_by_file, save_dimension_to_file
from backend.modules.dna_chain.dna_registry import register_mutation_proposal
from backend.modules.hexcore.memory_engine import store_memory as store_memory_entry

# ─── 🧬 Glyph Mutation Engine ───────────────────────────────────────────────────

def mutate_glyph(container_path: str, coord: str, mutation: dict, reason: str) -> bool:
    """Apply a mutation to a glyph at a given coordinate and log the proposal."""
    dimension = load_dimension_by_file(container_path)
    grid = dimension.get("microgrid", {})
    old = json.dumps(grid.get(coord, {}), indent=2)

    if coord not in grid:
        print(f"[❌] Glyph at {coord} not found in {container_path}")
        return False

    # Backup original dimension
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
        "coord": coord,
        "reason": reason,
        "replaced_code": old,
        "new_code": new,
        "diff": diff,
        "impact_score": score_impact(old, new),
        "safety_score": score_safety(mutation),
        "soul_law_pass": check_soul_law(mutation),
        "symbolic_hash": symbolic_hash(grid[coord].get("value", "")),
        "approved": False,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    register_mutation_proposal(proposal)
    store_memory_entry("mutation_proposal", proposal)
    print(f"✅ Mutation proposal logged for glyph {coord}")
    return True

# ─── 🆕 CodexCore Compatibility: propose_mutation wrapper ──────────────────────

def propose_mutation(glyph: dict, reason: str = "CodexCore runtime execution") -> dict:
    """
    External interface to submit a mutation proposal based on glyph structure.
    This avoids circular imports by skipping StrategyPlanner and GoalEngine.
    """
    coord = glyph.get("coord", "unknown")
    file_path = glyph.get("file", "unknown_container.json")
    value = glyph.get("value", "undefined")
    tag = glyph.get("tag", "unlabeled")

    mutation = {
        "value": value,
        "tag": tag,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }

    mutate_glyph(file_path, coord, mutation, reason=reason)
    return {
        "status": "proposed",
        "coord": coord,
        "file": file_path,
        "value": value,
        "tag": tag
    }

# ─── ♻️ Auto-Mutation via Decay Limit ──────────────────────────────────────────

def auto_mutate_if_expired(container_path: str, coord: str, now_ms: Optional[int] = None, fallback_value: str = "rebirth") -> bool:
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
        return False  # No decay logic

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

# ─── 🔁 Self-Rewriting Logic via ⬁ Glyphs ──────────────────────────────────────

def run_self_rewrite(container_path: str, coord: str) -> bool:
    """Execute a self-rewriting glyph if it encodes ⬁ logic."""
    dimension = load_dimension_by_file(container_path)
    grid = dimension.get("microgrid", {})

    if coord not in grid:
        return False

    glyph = grid[coord]
    value = glyph.get("value", "")
    if "⬁" in value or "→ ⬁" in value:
        print(f"[🔁] Self-rewriting triggered for glyph at {coord}")
        mutated_value = rewrite_value(value)
        mutation = {
            "value": mutated_value,
            "tag": "self_rewritten",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        return mutate_glyph(container_path, coord, mutation, reason="Self-rewriting logic executed")
    return False

def rewrite_value(old_value: str) -> str:
    """Basic symbolic rewrite simulation for ⬁ logic."""
    if "→ ⬁" in old_value:
        return old_value.replace("→ ⬁", "→ Reflect")
    return f"{old_value} + Echo"

# ─── 📊 Mutation Scoring + Ethics ──────────────────────────────────────────────

def score_impact(old: str, new: str) -> float:
    """Assign impact score based on change magnitude."""
    return 1.0 if old != new else 0.0

def score_safety(mutation: dict) -> float:
    """Simple filter for dangerous words."""
    val = json.dumps(mutation)
    if any(x in val for x in ["Kill", "Destroy", "Exploit"]):
        return 0.0
    return 1.0

def check_soul_law(mutation: dict) -> bool:
    """Ensure mutation does not violate Soul Laws."""
    val = json.dumps(mutation)
    banned = ["Harm", "Lie", "Dominate"]
    return not any(x in val for x in banned)

# ─── 🧬 Symbolic Hash (for deduplication) ──────────────────────────────────────

def symbolic_hash(glyph: str) -> str:
    """Generate stable symbolic hash for glyph content."""
    return hashlib.sha256(glyph.strip().encode("utf-8")).hexdigest()