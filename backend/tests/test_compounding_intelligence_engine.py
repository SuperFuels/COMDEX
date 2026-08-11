from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.compounding_intelligence_engine import (
    CAMPAIGNS,
    run,
    run_substrate_tournament,
)


ROOT = Path(__file__).resolve().parents[2]


def _provider_factory(model: str, _: Path):
    def provider(prompt: str):
        campaign = next(row for row in CAMPAIGNS if row["objective"] in prompt)
        proposal = {
            "capabilities": list(campaign["subjects"]),
            "success_criterion": "fresh independent executable outcome and later recheck",
            "steps": ["interpret", "retrieve", "construct", "falsify", "execute"],
            "counterexamples": ["wrong mechanism", "execution confounder"],
            "escalation": "abstain when no authority can decide",
        }
        return {"available": True, "response": json.dumps(proposal), "latency_ms": 1.0}
    return provider


def test_six_domain_substrate_tournament_is_proposal_only(tmp_path: Path) -> None:
    result = run_substrate_tournament(
        repo_root=ROOT,
        models=("candidate_a", "candidate_b"),
        cache_dir=tmp_path,
        provider_factory=_provider_factory,
    )
    assert result["challenger_promoted"] is True
    assert result["campaigns"] == 6
    assert result["unsafe_acceptances"] == 0
    assert "no execution or truth authority" not in result["authority_boundary"].lower()


def test_compounding_engine_integrates_all_six_campaigns(tmp_path: Path) -> None:
    tournament = run_substrate_tournament(
        repo_root=ROOT,
        models=("candidate",),
        cache_dir=tmp_path / "cache",
        provider_factory=_provider_factory,
    )
    retained = tmp_path / "substrate_tournament.json"
    retained.parent.mkdir(parents=True, exist_ok=True)
    retained.write_text(json.dumps(tournament, indent=2, sort_keys=True), encoding="utf-8")
    result = run(
        repo_root=ROOT,
        result_path=tmp_path / "result.json",
        state_path=tmp_path / "state.json",
        live_substrates=False,
        tournament_path=retained,
    )
    assert result["passed"] is True
    assert result["gate"]["functional_reconstructions"] == 6
    assert result["gate"]["active_integrated_campaigns"] == 6
    assert result["gate"]["competency_awards"] == 0
    assert result["substrate_tournament"]["retained_without_requery"] is True
    assert len(result["campaign_portfolio"]) == 6
