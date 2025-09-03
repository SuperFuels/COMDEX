# backend/modules/dna_chain/mutation_checker.py
"""
🧬 mutation_checker.py

🚨 Glyph Mutation Compliance Checker
Analyzes symbolic diffs for violations of Soul Laws and logs mutation context.

Design Rubric:
- 🧠 Glyph Diff (from → to) .......................... ✅
- 🔐 Soul Law Violation Detection .................... ✅
- 📉 Entropy Delta Estimation ........................ ✅
- 📦 Container + Coord Awareness ..................... ✅
- 🧩 Knowledge Graph Injection ........................ ✅
"""

import re
import json
from typing import List, Dict, Optional
from backend.modules.soul.soul_laws import get_soul_laws
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

def check_mutation_against_soul_laws(diff_text: str) -> List[Dict]:
    """
    Evaluate mutation diff against defined Soul Laws.
    Returns a list of violations with law metadata if any are found.
    """
    violations = []
    laws = get_soul_laws()

    for law in laws:
        for trigger in law.get("triggers", []):
            if re.search(rf"\b{re.escape(trigger)}\b", diff_text, re.IGNORECASE):
                violations.append({
                    "law_id": law["id"],
                    "title": law["title"],
                    "trigger": trigger,
                    "severity": law.get("severity", "medium")
                })

    return violations

def estimate_entropy_change(before: str, after: str) -> float:
    """
    Naive entropy delta estimation based on unique token change.
    """
    tokens_before = set(before.split())
    tokens_after = set(after.split())
    delta = len(tokens_after.symmetric_difference(tokens_before)) / max(len(tokens_before.union(tokens_after)), 1)
    return round(delta, 3)

def add_dna_mutation(
    from_glyph,
    to_glyph,
    container: Optional[str] = None,
    coord: Optional[str] = None,
    label: str = "dna_mutation"
):
    """
    Inject a glyph mutation event into the Knowledge Graph.
    Ensures string serialization and SoulLaw compliance.
    """
    def ensure_str(val):
        if isinstance(val, dict):
            return json.dumps(val, ensure_ascii=False, indent=2)
        return str(val)

    # ✅ Serialize inputs
    from_glyph_str = ensure_str(from_glyph)
    to_glyph_str = ensure_str(to_glyph)

    # ✅ Create string diff
    diff_str = f"{from_glyph_str.strip()} ⟶ {to_glyph_str.strip()}"

    # ✅ Run checks
    entropy_delta = estimate_entropy_change(from_glyph_str, to_glyph_str)
    violations = check_mutation_against_soul_laws(diff_str)

    # ✅ Inject mutation into KG
    writer = get_kg_writer()
    writer.inject_glyph(
        content=str(diff_str) if not isinstance(diff_str, str) else diff_str,  # Must be str, never dict
        glyph_type="mutation",
        metadata={
            "source": "DNA",
            "label": label,
            "violations": violations,
            "entropy_delta": entropy_delta,
            "from": from_glyph_str,
            "to": to_glyph_str,
            "container": container,
            "coord": coord,
        },
        trace=f"{container}:{coord}" if container and coord else None
    )