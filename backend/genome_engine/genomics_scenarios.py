from __future__ import annotations
from typing import Any, Dict, List

def matched_key_case() -> Dict[str, Any]:
    return {"scenario_id": "matched_key", "mode": "matched", "k": 1, "mutation": None}

def mismatched_key_case() -> Dict[str, Any]:
    return {"scenario_id": "mismatched_key", "mode": "mismatch", "k": 1, "mutation": None}

def multiplex_case(k: int = 2) -> Dict[str, Any]:
    return {"scenario_id": f"multiplex_k{k}", "mode": "multiplex", "k": int(k), "mutation": None}

def mutation_case(target_channel: int = 0, severity: int = 512) -> Dict[str, Any]:
    # severity = number of positions/ticks to corrupt (deterministic baseline)
    return {
        "scenario_id": f"mutation_ch{int(target_channel)}_sev{int(severity)}",
        "mode": "mutation",
        "k": 2,
        "mutation": {"target_channel": int(target_channel), "severity": int(severity)},
    }

def default_scenarios() -> List[Dict[str, Any]]:
    return [
        matched_key_case(),
        mismatched_key_case(),
        multiplex_case(2),
        mutation_case(0, 512),
    ]
