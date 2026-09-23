from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/hexcore_programming_intelligence_closure.json"
HANDOFF = ROOT / "results/aion_programming_external_handoff_manifest.json"


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_internal_programming_closure_gate_passes() -> None:
    result = _result()
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["independent_repository_authorities"] >= 5
    assert gate["languages"] >= 3
    assert gate["three_seed_stability"] is True
    assert gate["self_invented_falsification"] is True
    assert gate["malicious_candidates_rejected"] == gate["malicious_candidates_total"]
    assert gate["unsafe_acceptances"] == 0


def test_router_is_conditional_and_beats_both_controls() -> None:
    result = _result()
    gate = result["gate"]
    assert gate["router_success"] == 1.0
    assert gate["router_weakest"] == 1.0
    assert gate["router_routes_used"] >= 3
    assert gate["router_beats_always_documentation"] is True
    assert gate["router_beats_never_memory"] is True


def test_external_handoff_is_frozen_but_not_self_certified() -> None:
    result = _result()
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    assert result["gate"]["external_bundle_frozen"] is True
    assert result["gate"]["externally_administered"] is False
    assert handoff["internal_promotion_is_not_external_certification"] is True
    assert len(handoff["frozen_inputs"]) == 6
    assert len(handoff["answer_commitment"]) == 64
