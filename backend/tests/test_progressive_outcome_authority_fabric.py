from pathlib import Path

from backend.modules.hexcore.progressive_competency_executor import RUNNERS
from backend.modules.hexcore.progressive_outcome_authority_fabric import (
    ProgressiveOutcomeAuthorityFabric,
)


def test_authority_families_qualify_subject_adapters(tmp_path: Path):
    fabric = ProgressiveOutcomeAuthorityFabric(state_path=tmp_path / "fabric.json")
    available = {sid for sid, row in fabric.state["adapters"].items()
                 if row["status"] == "verified_available"}
    assert available == {
        "mathematics", "english", "research_communication",
        "scientific_method", "data_statistics", "machine_learning_ai",
        "markets_investing", "probability_statistics",
        "accounting_corporate_finance", "financial_mathematics",
        "power_institutions_legitimacy", "information_intelligence_attention",
        "strategic_assets_capital_allocation", "technology_industry_platforms",
        "networks_talent_coordination", "resilience_geography_long_horizon",
        "cybersecurity", "application_web_api_security", "network_wireless_security",
        "cloud_identity_container_security", "adversary_emulation_penetration_testing",
        "exploit_analysis_reverse_engineering",
        "detection_threat_hunting_incident_response", "cryptography_protocol_security",
        "hardware_embedded_ot_security", "security_research_disclosure",
        "security_architecture_operations",
        "probabilistic_forecasting_calibration", "prediction_market_microstructure",
        "event_evidence_resolution_research", "elections_polling_public_opinion",
        "prediction_market_design_compliance",
    }
    assert {row["family"] for row in fabric.state["adapters"].values()} == {
        "proof_and_calculation", "document_and_delayed_question",
        "empirical_dataset_or_experiment", "data_and_statistical_outcome",
        "code_and_system_execution",
        "market_and_risk_execution",
        "probability_and_inference", "accounting_and_valuation",
        "financial_proof_and_pricing",
        "strategic_stewardship_decision",
        "authorized_cyber_range",
        "governed_prediction_market",
    }
    assert all(row["counterexamples_rejected"] == row["counterexamples_total"]
               for row in fabric.state["adapters"].values())


def test_family_adapter_executes_requested_subskill_and_rejects_counterexample(tmp_path: Path):
    fabric = ProgressiveOutcomeAuthorityFabric(state_path=tmp_path / "fabric.json")
    cases = {
        "mathematics": "proof",
        "english": "ambiguity",
        "research_communication": "citation",
        "scientific_method": "causal_inference",
        "data_statistics": "time_series",
        "machine_learning_ai": "evaluation",
        "markets_investing": "risk",
        "probability_statistics": "bayesian_reasoning",
        "accounting_corporate_finance": "valuation",
        "financial_mathematics": "no_arbitrage",
        "power_institutions_legitimacy": "legitimacy",
        "information_intelligence_attention": "source_criticism",
        "strategic_assets_capital_allocation": "valuation",
        "technology_industry_platforms": "platform_economics",
        "networks_talent_coordination": "incentive_alignment",
        "resilience_geography_long_horizon": "resilience",
        "cybersecurity": "threat_models",
        "application_web_api_security": "authorization",
        "network_wireless_security": "segmentation",
        "cloud_identity_container_security": "identity_access_management",
        "adversary_emulation_penetration_testing": "scope_authorization",
        "exploit_analysis_reverse_engineering": "memory_safety",
        "detection_threat_hunting_incident_response": "detection_logic",
        "cryptography_protocol_security": "nonce_replay_safety",
        "hardware_embedded_ot_security": "secure_updates",
        "security_research_disclosure": "authorization",
        "security_architecture_operations": "vulnerability_management",
        "probabilistic_forecasting_calibration": "calibration",
        "prediction_market_microstructure": "position_sizing",
        "event_evidence_resolution_research": "resolution_rules",
        "elections_polling_public_opinion": "poll_aggregation",
        "prediction_market_design_compliance": "jurisdiction",
    }
    for subject_id, skill in cases.items():
        result = fabric.run(subject_id, {
            "requirement": {"kind": "knowledge_test", "subskills": [skill]}
        }, [])
        assert result["passed"] is True
        assert result["gate"]["counterexamples_rejected"] == 1
        assert result["gate"]["unsafe_variants_rejected"] == 6


def test_verified_family_adapters_are_installed_in_progressive_runtime():
    for subject_id in (
        "mathematics", "english", "research_communication",
        "scientific_method", "data_statistics", "machine_learning_ai",
        "markets_investing", "probability_statistics",
        "accounting_corporate_finance", "financial_mathematics",
        "power_institutions_legitimacy", "information_intelligence_attention",
        "strategic_assets_capital_allocation", "technology_industry_platforms",
        "networks_talent_coordination", "resilience_geography_long_horizon",
        "cybersecurity", "application_web_api_security", "network_wireless_security",
        "cloud_identity_container_security", "adversary_emulation_penetration_testing",
        "exploit_analysis_reverse_engineering",
        "detection_threat_hunting_incident_response", "cryptography_protocol_security",
        "hardware_embedded_ot_security", "security_research_disclosure",
        "security_architecture_operations",
        "probabilistic_forecasting_calibration", "prediction_market_microstructure",
        "event_evidence_resolution_research", "elections_polling_public_opinion",
        "prediction_market_design_compliance",
    ):
        assert subject_id in RUNNERS
