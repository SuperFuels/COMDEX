from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.comprehensive_expertise_curriculum import (
    build_curriculum,
    run_comprehensive_expertise_curriculum_phase,
    select_portfolio,
    validate_curriculum,
)


def test_curriculum_is_deep_acyclic_and_cross_domain() -> None:
    curriculum = build_curriculum()
    assert curriculum["curriculum_digest"] == build_curriculum()["curriculum_digest"]
    validation = validate_curriculum(curriculum)
    assert validation["valid"] is True
    assert validation["learning_capabilities"] >= 18
    assert validation["subjects"] >= 90
    assert validation["domains"] >= 10
    assert validation["bridges"] >= 68
    assert validation["capstones"] >= 10
    assert validation["prerequisite_graph_acyclic"] is True
    assert validation["all_domains_bridged"] is True
    assert curriculum["assessment_protocol"]["self_scoring_cannot_award_competence"] is True
    assert curriculum["expansion_protocol"]["no_finite_syllabus_stop"] is True
    finance = set(curriculum["domains"]["economics_finance"])
    assert {
        "financial_mathematics", "stochastic_processes_finance", "financial_econometrics",
        "quantitative_research", "asset_pricing", "derivatives_structured_products",
        "portfolio_construction", "financial_risk_management",
        "market_microstructure_execution", "systematic_trading",
        "fundamental_equity_credit", "financial_regulation_compliance",
        "hedge_fund_operations", "institutional_banking_treasury",
        "alternative_private_markets", "tax_wealth_structuring",
        "financial_data_infrastructure",
    } <= finance
    assert any(row["project_id"] == "governed_quantitative_fund"
               for row in curriculum["capstones"])
    assert {
        "power_institutions_legitimacy", "information_intelligence_attention",
        "strategic_assets_capital_allocation", "technology_industry_platforms",
        "networks_talent_coordination", "resilience_geography_long_horizon",
    } <= set(curriculum["subjects"])
    assert any(row["project_id"] == "governed_strategic_asset_portfolio"
               for row in curriculum["capstones"])
    assert {
        "application_web_api_security", "network_wireless_security",
        "cloud_identity_container_security", "adversary_emulation_penetration_testing",
        "exploit_analysis_reverse_engineering",
        "detection_threat_hunting_incident_response", "cryptography_protocol_security",
        "hardware_embedded_ot_security", "security_research_disclosure",
        "security_architecture_operations",
    } <= set(curriculum["subjects"])
    assert any(row["project_id"] == "owned_purple_team_cyber_range"
               for row in curriculum["capstones"])
    assert {
        "probabilistic_forecasting_calibration", "prediction_market_microstructure",
        "event_evidence_resolution_research", "elections_polling_public_opinion",
        "prediction_market_design_compliance",
    } <= set(curriculum["subjects"])
    assert any(row["project_id"] == "governed_prediction_market_fund"
               for row in curriculum["capstones"])


def test_drone_problem_selects_multi_domain_expertise() -> None:
    curriculum = build_curriculum()
    portfolio = select_portfolio(
        curriculum,
        "Develop a safe cheap intelligent drone with battery endurance, payload, embedded software, manufacturing and legal constraints.",
    )
    selected = set(portfolio["selected_subjects"])
    assert portfolio["cross_domain"] is True
    assert len(portfolio["domains"]) >= 5
    assert "uncrewed_aerial_systems" in selected
    assert "energy_storage" in selected
    assert "embedded_systems" in selected
    assert "manufacturing_quality" in selected
    assert "law_regulation_ethics" in selected


def test_phase_builds_persistent_hash_checked_artifacts(tmp_path: Path) -> None:
    curriculum_path = tmp_path / "curriculum.json"
    result_path = tmp_path / "result.json"
    result = run_comprehensive_expertise_curriculum_phase(
        curriculum_path=curriculum_path,
        result_path=result_path,
    )
    assert result["passed"] is True
    assert result["gate"]["all_scenarios_cross_domain"] is True
    assert result["gate"]["no_competence_awarded"] is True
    assert result["gate"]["paid_api_calls"] == 0
    assert result["gate"]["unsafe_actions"] == 0
    assert json.loads(curriculum_path.read_text())["curriculum_digest"]
    assert json.loads(result_path.read_text())["result_digest"]
