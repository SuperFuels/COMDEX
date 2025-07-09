# mutation_scorer.py
# 🧠 Rule-based mutation scoring + logging

from typing import Dict
from datetime import datetime
from backend.modules.dna_chain.dna_registry import update_dna_proposal, load_registry, save_registry
from backend.modules.hexcore.memory_engine import MemoryEngine

# Scoring weights for glyph fields
TAG_WEIGHT = 1.0
VALUE_WEIGHT = 1.5
ACTION_WEIGHT = 2.0

# Optional keywords for safety/risk heuristics
RISKY_KEYWORDS = ["exec(", "eval(", "os.system", "subprocess", "open(", "delete", "rollback"]


def score_mutation(glyph: Dict) -> Dict[str, float]:
    """Calculate a mutation score based on glyph fields."""
    score = 0.0
    details = {}

    if glyph.get("tag"):
        details["tag"] = TAG_WEIGHT
        score += TAG_WEIGHT
    if glyph.get("value"):
        details["value"] = VALUE_WEIGHT
        score += VALUE_WEIGHT
    if glyph.get("action"):
        details["action"] = ACTION_WEIGHT
        score += ACTION_WEIGHT

    # Coord complexity
    coord_len = len(glyph.get("coord", ""))
    coord_score = min(1.0, coord_len * 0.1)
    details["coord"] = coord_score
    score += coord_score

    # Risk penalty (basic safety score)
    new_code = glyph.get("code", "")
    risk_flags = sum(kw in new_code for kw in RISKY_KEYWORDS)
    safety_score = max(0.0, 1.0 - (risk_flags * 0.1))
    details["safety"] = round(safety_score, 2)
    score *= safety_score

    return {
        "total": round(score, 2),
        "breakdown": details
    }


def process_and_score_mutation(proposal_id: str, glyph: Dict):
    """Score the mutation and store in registry + memory."""
    result = score_mutation(glyph)
    score = result["total"]
    breakdown = result["breakdown"]

    # Update DNA proposal
    update_dna_proposal(proposal_id, {
        "score": score,
        "score_breakdown": breakdown
    })

    # Log to memory
    MemoryEngine.store({
        "type": "mutation_score",
        "timestamp": datetime.utcnow().isoformat(),
        "proposal_id": proposal_id,
        "score": score,
        "glyph": glyph,
        "breakdown": breakdown,
        "role": "system",
        "tags": ["dna", "scoring", "mutation"]
    })

    print(f"[📊] Scored mutation {proposal_id}: {score}")
    return score