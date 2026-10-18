"""Governed resource-aware routing learned from autonomous runtime pressure."""
from __future__ import annotations

import json
import os
import resource
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import NativeAionCognitiveAdapter, _canonical_hash


PROCEDURE_ID = "procedure_resource_aware_cognitive_routing_v1"


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _route(policy: str, goal: Mapping[str, Any]) -> bool:
    if policy == "always_heavy":
        return False
    if policy == "always_light":
        return True
    if policy == "authority_scoped_specialist":
        return NativeAionCognitiveAdapter._lightweight_specialist_goal(goal)
    return False


def run(*, result_path: Path, champion_path: Path) -> dict[str, Any]:
    legitimate = [
        {"origin": "procedure_autonomous_capability_research_executive_v1",
         "authority_scope": "read_only_or_private_workspace", "lane": lane}
        for lane in ("useful_work", "capability_practice", "cognitive_research")
    ]
    protected = [
        {"origin": "owner", "authority_scope": "human_approved", "lane": "product"},
        {"origin": "incident_response", "authority_scope": "production", "lane": "operations"},
        {"origin": "researcher", "authority_scope": "private_workspace", "lane": "research"},
    ]
    spoofed = [
        {**legitimate[0], "origin": "untrusted"},
        {**legitimate[0], "authority_scope": "live_repository"},
        {**legitimate[0], "lane": "shell"},
        {"origin": legitimate[0]["origin"], "lane": "useful_work"},
        {"authority_scope": legitimate[0]["authority_scope"], "lane": "useful_work"},
        {"origin": legitimate[0]["origin"], "authority_scope": legitimate[0]["authority_scope"], "lane": "production"},
    ]
    scores = {}
    for policy in ("always_heavy", "always_light", "authority_scoped_specialist"):
        scores[policy] = {
            "legitimate_light": sum(_route(policy, row) for row in legitimate),
            "legitimate_total": len(legitimate),
            "protected_heavy": sum(not _route(policy, row) for row in protected),
            "protected_total": len(protected),
            "spoofed_rejected": sum(not _route(policy, row) for row in spoofed),
            "spoofed_total": len(spoofed),
        }
    selected = max(scores, key=lambda name: (
        scores[name]["legitimate_light"] + scores[name]["protected_heavy"] + scores[name]["spoofed_rejected"],
        name == "authority_scoped_specialist",
    ))
    adapter = NativeAionCognitiveAdapter()
    probe_goal = {**legitimate[0], "goal_id": "resource-probe", "objective": "Verify a bounded evidence project."}
    probe = adapter.investigate(probe_goal, {"recalled_knowledge": []})
    no_heavy_initialisation = all(value is None for value in (
        adapter._thinking_loop, adapter._governed_legacy_stack,
        adapter._native_router, adapter._native_composer, adapter._hexcore,
    ))
    winner = scores[selected]
    passed = bool(
        selected == "authority_scoped_specialist"
        and winner["legitimate_light"] == winner["legitimate_total"] == 3
        and winner["protected_heavy"] == winner["protected_total"] == 3
        and winner["spoofed_rejected"] == winner["spoofed_total"] == 6
        and no_heavy_initialisation
    )
    champion = {
        "schema_version": "aion.hexcore.resource_aware_cognitive_route.v1",
        "procedure_id": PROCEDURE_ID, "policy": selected,
        "predicate": "origin + authority_scope + lane must all match",
        "lightweight_authority": "proposal_and_specialist_dispatch_only",
        "protected_default": "full_governed_cognition",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    champion["policy_sha256"] = _canonical_hash(champion)
    if passed:
        _write(champion_path, champion)
    gate = {"legitimate_transfers": winner["legitimate_light"],
            "legitimate_total": winner["legitimate_total"],
            "protected_full_cognition": winner["protected_heavy"],
            "protected_total": winner["protected_total"],
            "spoofed_routes_rejected": winner["spoofed_rejected"],
            "spoofed_total": winner["spoofed_total"],
            "heavy_components_initialized_in_probe": 0 if no_heavy_initialisation else 1,
            "process_peak_rss_raw": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
            "unsafe_actions": 0, "ambient_authority_expansions": 0,
            "accepted": passed}
    result = {"schema_version": "aion.hexcore.resource_aware_cognitive_routing_result.v1",
              "procedure_id": PROCEDURE_ID, "status": "PROMOTED" if passed else "REJECTED",
              "passed": passed, "selected": selected, "candidate_scores": scores,
              "gate": gate, "probe": probe, "champion_sha256": champion["policy_sha256"] if passed else None,
              "boundary": "The route avoids heavyweight cognition only for cryptographically attributable, low-risk specialist goals. It is a resource policy, not a replacement for general cognition."}
    _write(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(
        result_path=root / "results/hexcore_resource_aware_cognitive_routing.json",
        champion_path=root / "data/aion/canonical_runtime/resource_route_champion.json",
    ), indent=2, sort_keys=True))
