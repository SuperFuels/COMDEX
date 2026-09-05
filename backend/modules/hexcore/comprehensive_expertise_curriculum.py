"""Comprehensive expertise and cross-domain synthesis curriculum for AION.

This module defines curriculum structure only. It does not award competence.
Every competence remains evidence-gated by source-disjoint assessment, practical
outcomes, delayed retention and independent authority appropriate to the field.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from backend.modules.hexcore.persistent_learning import _canonical_hash, _utc_timestamp


SCHEMA = "aion.hexcore.comprehensive_expertise_curriculum.v1"
LEVELS = (
    "unassessed",
    "aware",
    "functional",
    "proficient",
    "expert",
    "research_capable",
)


def _cap(capability_id: str, name: str, outcomes: Sequence[str]) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "name": name,
        "kind": "learning_capability",
        "outcomes": list(outcomes),
        "assessment": [
            "unfamiliar_problem",
            "source_disjoint_transfer",
            "error_diagnosis_and_repair",
            "delayed_closed_book_reuse",
        ],
    }


LEARNING_CAPABILITIES = (
    _cap("learning_strategy", "Learning strategy and metacognition", (
        "diagnose_missing_knowledge", "choose_learning_depth", "plan_prerequisites",
        "monitor_comprehension", "change_strategy_after_failure")),
    _cap("information_ingestion", "Information ingestion", (
        "read_text_tables_diagrams_code", "extract_claims", "preserve_provenance",
        "deduplicate_sources", "detect_missing_context")),
    _cap("source_criticism", "Source evaluation and epistemics", (
        "rank_authority", "separate_fact_inference_opinion", "detect_conflict",
        "calibrate_confidence", "abstain_when_evidence_is_inadequate")),
    _cap("formalisation", "Formalisation and knowledge markup", (
        "define_terms", "convert_prose_to_structures", "write_equations_and_schemas",
        "represent_constraints", "produce_machine_checkable_claims")),
    _cap("decomposition", "Problem decomposition", (
        "identify_subproblems", "map_dependencies", "find_bottlenecks",
        "separate_known_from_unknown", "compose_verified_parts")),
    _cap("critical_reasoning", "Critical thinking and adversarial reasoning", (
        "test_assumptions", "generate_counterexamples", "detect_circularity",
        "compare_explanations", "steelman_and_attack_candidates")),
    _cap("mathematical_reasoning", "Mathematical reasoning", (
        "quantify", "derive", "estimate", "prove_or_bound", "check_dimensions")),
    _cap("scientific_reasoning", "Scientific and causal reasoning", (
        "form_hypotheses", "design_experiments", "control_confounding",
        "measure_uncertainty", "replicate")),
    _cap("systems_thinking", "Systems and consequence thinking", (
        "model_feedback", "trace_second_order_effects", "find_emergent_failure",
        "analyse_tradeoffs", "maintain_system_boundaries")),
    _cap("execution", "Execution and delivery", (
        "turn_goals_into_actions", "use_tools", "manage_dependencies",
        "verify_outputs", "complete_real_projects")),
    _cap("debugging_repair", "Debugging, repair and improvement", (
        "localise_failure", "produce_minimal_repair", "test_regression",
        "retain_repair", "avoid_repeat_failure")),
    _cap("communication", "Communication and teaching", (
        "explain_at_multiple_levels", "write_precisely", "ask_good_questions",
        "negotiate_meaning", "teach_and_assess_others")),
    _cap("creativity_invention", "Creativity and invention", (
        "generate_alternatives", "combine_distant_concepts", "measure_novelty",
        "prototype", "discard_attractive_failures")),
    _cap("cross_domain_synthesis", "Cross-domain synthesis", (
        "discover_bridge_variables", "transfer_methods", "join_constraints",
        "build_multi_domain_models", "derive_new_testable_designs")),
    _cap("real_world_grounding", "Real-world grounding", (
        "connect_models_to_measurements", "respect_physical_constraints",
        "cost_and_resource_actions", "observe_outcomes", "revise_from_reality")),
    _cap("research_frontier", "Research and frontier discovery", (
        "map_known_frontier", "find_open_questions", "search_literature",
        "propose_falsifiable_novelty", "seek_specialist_review")),
    _cap("safety_governance", "Safety, ethics and governance", (
        "classify_risk", "respect_law_consent_and_authority", "control_dual_use",
        "preserve_auditability", "stop_when_authority_is_missing")),
    _cap("retention_compounding", "Retention and compounding", (
        "compress_functional_memory", "retrieve_without_source", "retest_over_time",
        "prevent_interference", "extend_existing_knowledge_graph")),
)


def _subject(
    subject_id: str,
    name: str,
    domain: str,
    competencies: Sequence[str],
    *,
    prerequisites: Sequence[str] = (),
    keywords: Sequence[str] = (),
    risk: str = "ordinary",
) -> dict[str, Any]:
    return {
        "subject_id": subject_id,
        "name": name,
        "domain": domain,
        "competencies": list(competencies),
        "prerequisites": list(prerequisites),
        "keywords": sorted(set(keywords) | set(subject_id.split("_"))),
        "risk": risk,
        "target_level": "expert",
        "expert_gate": {
            "knowledge_exam": "source_disjoint",
            "practical_projects": 3,
            "unfamiliar_transfer_projects": 2,
            "failure_repairs": 2,
            "retention_days": [1, 7, 30, 90],
            "independent_authority_required": True,
            "teaching_demonstration_required": True,
        },
    }


SUBJECTS = (
    _subject("logic_proof", "Logic and proof", "mathematics", ("propositional_logic", "predicate_logic", "proof_methods", "formal_proof", "counterexamples"), keywords=("reasoning", "theorem")),
    _subject("algebra_geometry", "Algebra, geometry and trigonometry", "mathematics", ("algebra", "functions", "geometry", "trigonometry", "coordinate_systems")),
    _subject("calculus_analysis", "Calculus and mathematical analysis", "mathematics", ("limits", "derivatives", "integrals", "series", "differential_equations"), prerequisites=("algebra_geometry",)),
    _subject("linear_algebra", "Linear algebra", "mathematics", ("vectors", "matrices", "linear_maps", "eigenstructure", "numerical_linear_algebra"), prerequisites=("algebra_geometry",)),
    _subject("probability_statistics", "Probability and statistics", "mathematics", ("probability", "distributions", "estimation", "hypothesis_testing", "bayesian_reasoning", "uncertainty"), prerequisites=("algebra_geometry",)),
    _subject("discrete_optimization", "Discrete mathematics and optimisation", "mathematics", ("combinatorics", "graphs", "algorithms", "linear_programming", "constraint_optimisation", "operations_research"), prerequisites=("logic_proof", "algebra_geometry"), keywords=("route", "schedule", "optimise")),
    _subject("numerical_methods", "Numerical methods and simulation", "mathematics", ("floating_point", "approximation", "solvers", "error_bounds", "monte_carlo", "simulation"), prerequisites=("calculus_analysis", "linear_algebra", "probability_statistics")),

    _subject("scientific_method", "Scientific method and measurement", "physical_science", ("hypotheses", "experimental_design", "measurement", "causal_inference", "replication", "literature_review"), keywords=("experiment", "evidence", "research")),
    _subject("classical_physics", "Mechanics, waves and thermodynamics", "physical_science", ("mechanics", "fluids", "waves", "heat", "thermodynamics", "dimensional_analysis"), prerequisites=("calculus_analysis",), keywords=("flight", "aerodynamics", "energy")),
    _subject("electromagnetism", "Electricity, magnetism and optics", "physical_science", ("circuits", "fields", "electromagnetism", "optics", "electromagnetic_compatibility"), prerequisites=("calculus_analysis",)),
    _subject("chemistry_materials", "Chemistry and materials science", "physical_science", ("chemical_bonding", "thermochemistry", "electrochemistry", "polymers", "metals", "composites", "degradation"), prerequisites=("algebra_geometry",), keywords=("material", "battery", "corrosion")),
    _subject("earth_climate", "Earth, climate and environmental science", "physical_science", ("geology", "weather", "climate", "hydrology", "remote_sensing", "environmental_measurement"), prerequisites=("scientific_method",), keywords=("weather", "terrain", "climate")),

    _subject("cell_genetic_biology", "Cell, molecular and genetic biology", "life_science", ("cells", "biochemistry", "genetics", "gene_expression", "evolution", "experimental_biology"), prerequisites=("scientific_method", "chemistry_materials")),
    _subject("physiology_health", "Physiology, health and clinical evidence", "life_science", ("anatomy", "physiology", "pathology", "pharmacology", "epidemiology", "clinical_evidence"), prerequisites=("cell_genetic_biology", "probability_statistics"), risk="high_stakes"),
    _subject("ecology_microbiology", "Ecology and microbiology", "life_science", ("microorganisms", "ecosystems", "population_dynamics", "soil_biology", "biodiversity", "biosecurity"), prerequisites=("cell_genetic_biology",)),
    _subject("agronomy_soil", "Agronomy and soil science", "agriculture", ("soil", "plant_nutrition", "crop_cycles", "irrigation", "pest_management", "yield_measurement"), prerequisites=("ecology_microbiology", "earth_climate"), keywords=("farming", "farm", "crop", "agriculture")),
    _subject("animal_food_systems", "Animal, food and agricultural systems", "agriculture", ("animal_systems", "food_safety", "post_harvest", "farm_economics", "supply_chain", "sustainability"), prerequisites=("ecology_microbiology",), keywords=("farming", "food")),
    _subject("precision_agriculture", "Precision and autonomous agriculture", "agriculture", ("field_sensing", "geospatial_mapping", "variable_rate_control", "farm_automation", "yield_models", "decision_support"), prerequisites=("agronomy_soil", "data_science_ml", "sensors_instrumentation"), keywords=("drone", "crop", "farm", "precision")),

    _subject("computer_science", "Computer science and algorithms", "computing", ("data_structures", "algorithms", "complexity", "automata", "compilers", "computability"), prerequisites=("logic_proof", "discrete_optimization")),
    _subject("programming_languages", "Programming languages", "computing", ("python", "javascript_typescript", "rust", "c_cpp", "functional_programming", "language_interoperation"), prerequisites=("computer_science",), keywords=("code", "software")),
    _subject("software_engineering", "Software engineering", "computing", ("requirements", "architecture", "testing", "debugging", "version_control", "delivery", "maintenance"), prerequisites=("programming_languages",), keywords=("software", "application", "system")),
    _subject("data_databases", "Data engineering and databases", "computing", ("data_models", "sql", "transactions", "pipelines", "data_quality", "warehousing", "governance"), prerequisites=("programming_languages", "probability_statistics"), keywords=("data", "database")),
    _subject("operating_distributed_networks", "Operating, distributed and networked systems", "computing", ("operating_systems", "concurrency", "networks", "distributed_systems", "cloud", "reliability", "observability"), prerequisites=("software_engineering",)),
    _subject("cybersecurity", "Cybersecurity and privacy", "computing", ("threat_models", "secure_design", "cryptography", "network_security", "identity", "privacy", "incident_response", "supply_chain"), prerequisites=("operating_distributed_networks",), risk="dual_use"),
    _subject("application_web_api_security", "Application, web and API security", "computing", ("secure_coding", "authentication", "authorization", "session_security", "injection_defence", "browser_security", "api_security", "security_testing"), prerequisites=("cybersecurity", "software_engineering", "data_databases"), keywords=("appsec", "web security", "api", "owasp"), risk="dual_use"),
    _subject("network_wireless_security", "Network and wireless security", "computing", ("network_reconnaissance", "protocol_analysis", "segmentation", "firewalls", "secure_routing", "wireless_security", "vpn_zero_trust", "network_validation"), prerequisites=("cybersecurity", "operating_distributed_networks"), keywords=("network security", "wireless", "firewall", "vpn"), risk="dual_use"),
    _subject("cloud_identity_container_security", "Cloud, identity and container security", "computing", ("identity_access_management", "secrets", "cloud_posture", "container_security", "kubernetes_security", "serverless_security", "tenant_isolation", "continuous_assurance"), prerequisites=("cybersecurity", "operating_distributed_networks", "software_engineering"), keywords=("cloud security", "iam", "container", "kubernetes"), risk="dual_use"),
    _subject("adversary_emulation_penetration_testing", "Authorised adversary emulation and penetration testing", "computing", ("scope_authorization", "reconnaissance", "attack_surface_mapping", "vulnerability_validation", "controlled_exploitation", "privilege_boundary_testing", "evidence_preservation", "remediation_verification"), prerequisites=("application_web_api_security", "network_wireless_security", "law_regulation_ethics"), keywords=("penetration testing", "red team", "adversary emulation"), risk="dual_use"),
    _subject("exploit_analysis_reverse_engineering", "Exploit analysis and defensive reverse engineering", "computing", ("assembly_fundamentals", "debugging", "memory_safety", "binary_formats", "static_analysis", "dynamic_analysis", "exploit_mitigation", "malware_triage"), prerequisites=("cybersecurity", "operating_distributed_networks", "programming_languages"), keywords=("reverse engineering", "binary", "exploit analysis", "malware analysis"), risk="dual_use"),
    _subject("detection_threat_hunting_incident_response", "Detection engineering, threat hunting and incident response", "computing", ("telemetry", "detection_logic", "threat_hunting", "triage", "containment", "eradication", "recovery", "post_incident_learning"), prerequisites=("cybersecurity", "data_science_ml", "operating_distributed_networks"), keywords=("blue team", "detection", "incident response", "threat hunting"), risk="dual_use"),
    _subject("cryptography_protocol_security", "Applied cryptography and protocol security", "computing", ("cryptographic_primitives", "key_management", "tls", "authentication_protocols", "protocol_state_machines", "nonce_replay_safety", "side_channels", "formal_protocol_review"), prerequisites=("cybersecurity", "logic_proof", "probability_statistics"), keywords=("cryptography", "tls", "protocol", "keys"), risk="dual_use"),
    _subject("hardware_embedded_ot_security", "Hardware, embedded and operational-technology security", "computing", ("firmware_analysis", "hardware_roots_of_trust", "debug_interfaces", "embedded_networks", "industrial_protocols", "safety_boundaries", "secure_updates", "physical_cyber_incidents"), prerequisites=("cybersecurity", "embedded_systems", "electronics_circuits"), keywords=("firmware", "hardware security", "ics", "ot"), risk="dual_use"),
    _subject("security_research_disclosure", "Security research and responsible vulnerability disclosure", "computing", ("research_ethics", "authorization", "reproducibility", "severity", "minimal_proof", "vendor_coordination", "embargo", "public_disclosure"), prerequisites=("adversary_emulation_penetration_testing", "language_research_communication", "law_regulation_ethics"), keywords=("security research", "vulnerability disclosure", "cve"), risk="dual_use"),
    _subject("security_architecture_operations", "Security architecture and operational assurance", "computing", ("zero_trust_architecture", "security_controls", "asset_inventory", "vulnerability_management", "supply_chain_assurance", "business_continuity", "metrics", "security_governance"), prerequisites=("cloud_identity_container_security", "network_wireless_security", "detection_threat_hunting_incident_response"), keywords=("security architecture", "soc", "vulnerability management", "assurance"), risk="dual_use"),
    _subject("data_science_ml", "Data science, AI and machine learning", "computing", ("data_analysis", "machine_learning", "deep_learning", "evaluation", "causal_ml", "interpretability", "deployment"), prerequisites=("linear_algebra", "probability_statistics", "programming_languages"), keywords=("ai", "intelligent", "prediction", "vision")),
    _subject("human_computer_interaction", "Human-computer interaction", "computing", ("user_research", "interaction_design", "accessibility", "visualisation", "human_factors", "evaluation"), prerequisites=("software_engineering",), keywords=("interface", "product", "user")),

    _subject("electronics_circuits", "Electronics and circuit design", "engineering", ("analogue", "digital", "power_electronics", "pcb_design", "signal_integrity", "test_and_debug"), prerequisites=("electromagnetism",), keywords=("schematic", "circuit", "hardware")),
    _subject("sensors_instrumentation", "Sensors and instrumentation", "engineering", ("sensor_physics", "signal_conditioning", "sampling", "calibration", "sensor_fusion", "measurement_uncertainty"), prerequisites=("electronics_circuits", "probability_statistics"), keywords=("sensor", "measurement")),
    _subject("mechanical_cad", "Mechanical engineering and CAD", "engineering", ("statics", "dynamics", "mechanisms", "solid_mechanics", "cad", "thermal_design", "tolerances"), prerequisites=("classical_physics",), keywords=("mechanical", "frame", "schematic", "design")),
    _subject("control_robotics", "Control theory and robotics", "engineering", ("feedback", "stability", "state_estimation", "motion_planning", "robot_kinematics", "autonomy", "safety"), prerequisites=("linear_algebra", "calculus_analysis", "sensors_instrumentation"), keywords=("control", "robot", "autonomous", "flight")),
    _subject("embedded_systems", "Embedded hardware and software", "engineering", ("microcontrollers", "real_time", "firmware", "buses", "low_power", "hardware_software_codesign", "verification"), prerequisites=("electronics_circuits", "programming_languages"), keywords=("firmware", "controller", "embedded")),
    _subject("manufacturing_quality", "Manufacturing, quality and reliability", "engineering", ("process_selection", "design_for_manufacture", "tooling", "quality_control", "reliability", "failure_analysis", "costing"), prerequisites=("mechanical_cad", "chemistry_materials"), keywords=("manufacture", "factory", "cheap", "cost")),
    _subject("systems_engineering", "Systems engineering", "engineering", ("requirements", "interfaces", "trade_studies", "verification_validation", "risk", "lifecycle", "configuration"), prerequisites=("software_engineering", "mechanical_cad"), keywords=("system", "integrate", "requirements")),
    _subject("uncrewed_aerial_systems", "Uncrewed aerial systems and drones", "engineering", ("aerodynamics", "propulsion", "flight_control", "navigation", "payloads", "communications", "airworthiness", "operations"), prerequisites=("classical_physics", "control_robotics", "embedded_systems", "energy_storage"), keywords=("drone", "uav", "flight", "payload"), risk="dual_use"),

    _subject("energy_fundamentals", "Energy conversion and efficiency", "energy", ("energy_accounting", "conversion", "efficiency", "heat_transfer", "lifecycle_energy", "technoeconomics"), prerequisites=("classical_physics",), keywords=("energy", "power")),
    _subject("energy_storage", "Batteries and energy storage", "energy", ("electrochemistry", "cell_models", "battery_management", "thermal_safety", "degradation", "pack_design", "economics"), prerequisites=("chemistry_materials", "electronics_circuits", "energy_fundamentals"), keywords=("battery", "storage", "endurance")),
    _subject("generation_grids", "Energy generation, grids and microgrids", "energy", ("generation", "renewables", "grid_control", "power_flow", "microgrids", "resilience", "markets"), prerequisites=("energy_fundamentals", "electronics_circuits"), keywords=("solar", "grid", "microgrid", "renewable")),
    _subject("energy_policy_sustainability", "Energy policy and sustainability", "energy", ("emissions", "lifecycle_assessment", "policy", "regulation", "energy_markets", "environmental_justice"), prerequisites=("energy_fundamentals", "economics_core")),

    _subject("economics_core", "Microeconomics, macroeconomics and econometrics", "economics_finance", ("microeconomics", "macroeconomics", "incentives", "game_theory", "econometrics", "policy"), prerequisites=("probability_statistics",), keywords=("economy", "economic")),
    _subject("accounting_corporate_finance", "Accounting and corporate finance", "economics_finance", ("bookkeeping", "statements", "cost_accounting", "valuation", "capital_budgeting", "cash", "controls"), prerequisites=("algebra_geometry",), keywords=("finance", "accounting", "cost", "profit")),
    _subject("markets_investing", "Financial markets and investment", "economics_finance", ("market_structure", "assets", "portfolio_theory", "risk", "derivatives", "behaviour", "regulation"), prerequisites=("probability_statistics", "economics_core", "accounting_corporate_finance"), keywords=("stock", "market", "invest", "trading"), risk="high_stakes"),
    _subject("financial_mathematics", "Financial mathematics", "economics_finance", ("discounting", "returns", "no_arbitrage", "state_prices", "martingales", "change_of_measure", "convexity", "numerical_pricing"), prerequisites=("calculus_analysis", "linear_algebra", "probability_statistics"), keywords=("quant", "pricing", "financial mathematics"), risk="high_stakes"),
    _subject("stochastic_processes_finance", "Stochastic processes for finance", "economics_finance", ("random_walks", "markov_processes", "brownian_motion", "ito_calculus", "stochastic_differential_equations", "jump_processes", "filtering", "simulation"), prerequisites=("financial_mathematics", "numerical_methods"), keywords=("stochastic", "quant", "monte carlo"), risk="high_stakes"),
    _subject("financial_econometrics", "Financial econometrics and time series", "economics_finance", ("stationarity", "arima", "volatility_models", "cointegration", "factor_models", "state_space", "regime_change", "forecast_validation"), prerequisites=("probability_statistics", "linear_algebra", "economics_core"), keywords=("econometrics", "time series", "forecast", "quant"), risk="high_stakes"),
    _subject("quantitative_research", "Quantitative investment research", "economics_finance", ("hypothesis_design", "data_provenance", "feature_engineering", "backtesting", "cross_validation", "multiple_testing", "transaction_costs", "reproducibility"), prerequisites=("financial_mathematics", "financial_econometrics", "programming_languages", "data_science_ml"), keywords=("quant", "alpha", "backtest", "research"), risk="high_stakes"),
    _subject("asset_pricing", "Asset pricing and valuation", "economics_finance", ("present_value", "equilibrium_models", "factor_pricing", "term_structure", "equity_valuation", "credit_valuation", "liquidity_premia", "model_risk"), prerequisites=("financial_mathematics", "economics_core", "accounting_corporate_finance"), keywords=("asset pricing", "valuation", "factor", "credit"), risk="high_stakes"),
    _subject("derivatives_structured_products", "Derivatives and structured products", "economics_finance", ("forwards_futures", "options", "greeks", "volatility_surfaces", "fixed_income_derivatives", "credit_derivatives", "structured_products", "hedging"), prerequisites=("stochastic_processes_finance", "markets_investing"), keywords=("options", "derivatives", "volatility", "hedging"), risk="high_stakes"),
    _subject("portfolio_construction", "Portfolio construction and allocation", "economics_finance", ("mean_variance", "factor_exposures", "risk_budgeting", "robust_optimisation", "constraints", "rebalancing", "performance_attribution", "capacity"), prerequisites=("asset_pricing", "discrete_optimization", "markets_investing"), keywords=("portfolio", "allocation", "fund manager"), risk="high_stakes"),
    _subject("financial_risk_management", "Financial risk management", "economics_finance", ("market_risk", "credit_risk", "liquidity_risk", "counterparty_risk", "var_expected_shortfall", "stress_testing", "scenario_analysis", "model_governance"), prerequisites=("probability_statistics", "derivatives_structured_products", "accounting_corporate_finance"), keywords=("risk", "stress", "var"), risk="high_stakes"),
    _subject("market_microstructure_execution", "Market microstructure and execution", "economics_finance", ("order_books", "price_formation", "liquidity", "impact", "execution_algorithms", "slippage", "venue_selection", "trade_cost_analysis"), prerequisites=("markets_investing", "financial_econometrics"), keywords=("execution", "microstructure", "order book", "trading"), risk="high_stakes"),
    _subject("systematic_trading", "Systematic trading and alpha engineering", "economics_finance", ("signal_design", "portfolio_signals", "position_sizing", "execution_integration", "drawdown_control", "regime_robustness", "live_monitoring", "strategy_retirement"), prerequisites=("quantitative_research", "market_microstructure_execution", "financial_risk_management"), keywords=("systematic", "algorithmic trading", "alpha", "quant"), risk="high_stakes"),
    _subject("fundamental_equity_credit", "Fundamental equity and credit analysis", "economics_finance", ("financial_statement_analysis", "industry_analysis", "competitive_advantage", "earnings_quality", "cash_flow_forecasting", "capital_structure", "default_risk", "investment_memo"), prerequisites=("accounting_corporate_finance", "economics_core", "asset_pricing"), keywords=("equity", "credit", "fundamental", "analyst"), risk="high_stakes"),
    _subject("financial_regulation_compliance", "Financial regulation, compliance and conduct", "economics_finance", ("market_abuse", "fiduciary_duty", "client_suitability", "aml_kyc", "best_execution", "reporting", "model_governance", "jurisdiction"), prerequisites=("law_regulation_ethics", "markets_investing", "accounting_corporate_finance"), keywords=("compliance", "regulation", "conduct"), risk="high_stakes"),
    _subject("hedge_fund_operations", "Hedge-fund management and operations", "economics_finance", ("mandate_design", "capital_allocation", "prime_brokerage", "fund_accounting", "liquidity_terms", "operational_due_diligence", "investor_reporting", "governance"), prerequisites=("portfolio_construction", "financial_risk_management", "financial_regulation_compliance"), keywords=("hedge fund", "fund manager", "prime broker"), risk="high_stakes"),
    _subject("institutional_banking_treasury", "Banking, treasury and balance-sheet management", "economics_finance", ("banking_models", "asset_liability_management", "liquidity_buffers", "funding", "interest_rate_risk", "credit_creation", "payments", "treasury_controls"), prerequisites=("accounting_corporate_finance", "financial_risk_management", "markets_investing"), keywords=("banking", "treasury", "alm", "liquidity"), risk="high_stakes"),
    _subject("alternative_private_markets", "Alternative investments and private markets", "economics_finance", ("private_equity", "venture_capital", "private_credit", "real_assets", "commodities", "hedge_fund_strategies", "illiquidity", "manager_due_diligence"), prerequisites=("asset_pricing", "fundamental_equity_credit", "portfolio_construction"), keywords=("alternatives", "private equity", "venture", "commodities"), risk="high_stakes"),
    _subject("tax_wealth_structuring", "Tax, wealth and capital structuring", "economics_finance", ("tax_principles", "corporate_tax", "investment_tax", "cross_border", "pensions", "estates", "capital_structure", "professional_referral"), prerequisites=("accounting_corporate_finance", "law_regulation_ethics"), keywords=("tax", "wealth", "pension", "structuring"), risk="high_stakes"),
    _subject("financial_data_infrastructure", "Financial data and research infrastructure", "economics_finance", ("market_data", "reference_data", "corporate_actions", "point_in_time_data", "survivorship_bias", "research_platforms", "lineage", "production_controls"), prerequisites=("data_databases", "software_engineering", "markets_investing"), keywords=("financial data", "quant platform", "point in time", "lineage"), risk="high_stakes"),
    _subject("probabilistic_forecasting_calibration", "Probabilistic forecasting and calibration", "economics_finance", ("base_rates", "reference_classes", "bayesian_updates", "forecast_decomposition", "proper_scoring_rules", "calibration", "aggregation", "decision_thresholds"), prerequisites=("probability_statistics", "scientific_method"), keywords=("forecast", "probability", "calibration", "brier"), risk="high_stakes"),
    _subject("prediction_market_microstructure", "Prediction-market microstructure and execution", "economics_finance", ("binary_contracts", "order_books", "implied_probability", "fees_slippage", "liquidity", "position_sizing", "cross_market_coherence", "execution_controls"), prerequisites=("probabilistic_forecasting_calibration", "market_microstructure_execution", "financial_risk_management"), keywords=("prediction market", "polymarket", "kalshi", "event contract"), risk="high_stakes"),
    _subject("event_evidence_resolution_research", "Event evidence and resolution research", "human_society", ("question_decomposition", "source_hierarchy", "resolution_rules", "timeline_evidence", "conflicting_sources", "manipulation_risk", "audit_trail", "settlement_review"), prerequisites=("language_research_communication", "law_regulation_ethics", "probabilistic_forecasting_calibration"), keywords=("event", "resolution", "evidence", "forecast"), risk="high_stakes"),
    _subject("elections_polling_public_opinion", "Elections, polling and public-opinion analysis", "human_society", ("electoral_systems", "poll_sampling", "turnout_models", "poll_aggregation", "demographics", "campaign_dynamics", "forecast_error", "institutional_scenarios"), prerequisites=("history_geography_geopolitics", "probability_statistics", "psychology_organisations"), keywords=("election", "poll", "turnout", "politics"), risk="high_stakes"),
    _subject("prediction_market_design_compliance", "Prediction-market design, integrity and compliance", "business", ("objective_question_design", "resolution_authority", "market_demand", "manipulation_resistance", "insider_information", "jurisdiction", "proposal_governance", "post_settlement_review"), prerequisites=("prediction_market_microstructure", "event_evidence_resolution_research", "financial_regulation_compliance"), keywords=("market design", "prediction market", "compliance", "integrity"), risk="high_stakes"),
    _subject("power_institutions_legitimacy", "Power, institutions and legitimate authority", "human_society", ("institutional_power", "law_and_rules", "legitimacy", "trust", "accountability", "state_capacity", "governance", "power_failure_modes"), prerequisites=("history_geography_geopolitics", "negotiation_governance", "law_regulation_ethics"), keywords=("power", "institution", "legitimacy", "authority"), risk="dual_use"),
    _subject("information_intelligence_attention", "Information, intelligence and ethical attention systems", "human_society", ("intelligence_collection", "source_criticism", "uncertainty", "confidentiality", "narrative_analysis", "attention_systems", "misinformation_defence", "transparency"), prerequisites=("language_research_communication", "probability_statistics", "law_regulation_ethics"), keywords=("information", "intelligence", "narrative", "attention"), risk="dual_use"),
    _subject("strategic_assets_capital_allocation", "Strategic assets and capital allocation", "business", ("asset_thesis", "valuation", "control_rights", "optionality", "dependency_reduction", "build_buy_partner", "portfolio_allocation", "exit_discipline"), prerequisites=("accounting_corporate_finance", "business_strategy_operations", "financial_risk_management"), keywords=("strategic asset", "acquisition", "capital allocation", "ownership"), risk="high_stakes"),
    _subject("technology_industry_platforms", "Technology, industry, platforms and standards", "business", ("technology_forecasting", "industry_structure", "platform_economics", "standards_strategy", "intellectual_property", "compute_data_energy", "manufacturing_scale", "distribution_power"), prerequisites=("strategic_assets_capital_allocation", "systems_engineering", "economics_core"), keywords=("technology", "industry", "platform", "standard"), risk="high_stakes"),
    _subject("networks_talent_coordination", "Networks, talent and organisational coordination", "business", ("alliances", "talent_systems", "organisation_design", "incentive_alignment", "negotiation", "coordination", "culture", "succession"), prerequisites=("psychology_organisations", "negotiation_governance", "business_strategy_operations"), keywords=("network", "talent", "coordination", "organisation")),
    _subject("resilience_geography_long_horizon", "Geography, logistics, resilience and long-horizon strategy", "business", ("geographic_advantage", "logistics", "resource_security", "supply_dependencies", "defensive_security", "scenario_planning", "resilience", "strategic_patience"), prerequisites=("history_geography_geopolitics", "supply_chain_procurement", "strategic_assets_capital_allocation"), keywords=("geography", "logistics", "resilience", "long term"), risk="dual_use"),
    _subject("business_strategy_operations", "Business strategy and operations", "business", ("strategy", "business_models", "operations", "unit_economics", "metrics", "risk", "governance"), prerequisites=("accounting_corporate_finance",), keywords=("business", "operations", "company")),
    _subject("marketing_sales_customer", "Marketing, sales and customer systems", "business", ("research", "positioning", "channels", "sales_process", "pricing", "service", "retention"), prerequisites=("business_strategy_operations",), keywords=("marketing", "sales", "customer")),
    _subject("supply_chain_procurement", "Supply chain and procurement", "business", ("demand", "inventory", "sourcing", "logistics", "supplier_risk", "quality", "resilience"), prerequisites=("business_strategy_operations", "discrete_optimization"), keywords=("supply", "inventory", "procurement", "logistics")),
    _subject("entrepreneurship_innovation", "Entrepreneurship and innovation", "business", ("problem_discovery", "product", "experimentation", "business_model", "funding", "scaling", "responsible_innovation"), prerequisites=("business_strategy_operations", "marketing_sales_customer"), keywords=("startup", "product", "innovation")),

    _subject("language_research_communication", "Language, research and professional communication", "human_society", ("reading", "writing", "argument", "citation", "presentation", "teaching", "multilingual_communication"), keywords=("write", "research", "explain")),
    _subject("psychology_organisations", "Psychology and organisational behaviour", "human_society", ("cognition", "motivation", "decision_bias", "teams", "leadership", "culture", "change"), prerequisites=("scientific_method",)),
    _subject("history_geography_geopolitics", "History, geography and geopolitics", "human_society", ("historical_method", "physical_geography", "institutions", "trade", "conflict_analysis", "cultural_context"), keywords=("history", "geography", "geopolitics"), risk="dual_use"),
    _subject("law_regulation_ethics", "Law, regulation and applied ethics", "human_society", ("legal_research", "contracts", "privacy", "intellectual_property", "employment", "sector_regulation", "ethics", "jurisdiction"), prerequisites=("language_research_communication",), keywords=("law", "regulation", "legal", "ethics")),
    _subject("negotiation_governance", "Negotiation, governance and institutions", "human_society", ("negotiation", "stakeholders", "institution_design", "public_policy", "conflict_resolution", "accountability"), prerequisites=("psychology_organisations", "law_regulation_ethics")),

    _subject("water_waste_resilience", "Water, waste and resilient infrastructure", "environment_resilience", ("water_systems", "waste", "circularity", "infrastructure", "hazards", "resilience", "disaster_response"), prerequisites=("earth_climate", "systems_engineering"), keywords=("water", "waste", "disaster", "resilience")),
    _subject("design_creative_practice", "Design and creative practice", "creative", ("ideation", "visual_thinking", "industrial_design", "prototyping", "critique", "aesthetics", "communication"), prerequisites=("human_computer_interaction",), keywords=("design", "creative", "invent")),
)


def _bridge(source: str, target: str, relation: str, variables: Sequence[str]) -> dict[str, Any]:
    body = {
        "source": source,
        "target": target,
        "relation": relation,
        "bridge_variables": list(variables),
        "verification": ["derive_mapping", "test_counterexample", "apply_in_unfamiliar_project"],
    }
    body["bridge_id"] = "bridge_" + _canonical_hash(body)[:16]
    return body


CROSS_DOMAIN_BRIDGES = (
    _bridge("linear_algebra", "data_science_ml", "enables", ("vectors", "matrices", "eigenstructure")),
    _bridge("probability_statistics", "data_science_ml", "measures_uncertainty_in", ("likelihood", "calibration", "generalisation")),
    _bridge("discrete_optimization", "supply_chain_procurement", "optimizes", ("route", "inventory", "capacity")),
    _bridge("control_robotics", "uncrewed_aerial_systems", "stabilizes_and_guides", ("state", "feedback", "trajectory")),
    _bridge("energy_storage", "uncrewed_aerial_systems", "constrains", ("energy_density", "mass", "endurance", "thermal_safety")),
    _bridge("embedded_systems", "uncrewed_aerial_systems", "implements", ("flight_loop", "sensors", "communications", "power")),
    _bridge("mechanical_cad", "uncrewed_aerial_systems", "shapes", ("mass", "drag", "strength", "payload")),
    _bridge("manufacturing_quality", "uncrewed_aerial_systems", "makes_economically_real", ("tolerance", "yield", "unit_cost", "reliability")),
    _bridge("law_regulation_ethics", "uncrewed_aerial_systems", "governs", ("airspace", "privacy", "airworthiness", "operator_duty")),
    _bridge("cybersecurity", "uncrewed_aerial_systems", "protects", ("command_link", "firmware", "identity", "safety")),
    _bridge("software_engineering", "application_web_api_security", "secures", ("design", "testing", "dependency", "release")),
    _bridge("operating_distributed_networks", "network_wireless_security", "exposes_and_defends", ("protocol", "boundary", "routing", "telemetry")),
    _bridge("data_databases", "cloud_identity_container_security", "protects", ("identity", "secret", "tenant", "lineage")),
    _bridge("application_web_api_security", "adversary_emulation_penetration_testing", "validates", ("authorization", "surface", "proof", "remediation")),
    _bridge("programming_languages", "exploit_analysis_reverse_engineering", "explains", ("memory", "binary", "debug", "mitigation")),
    _bridge("data_science_ml", "detection_threat_hunting_incident_response", "detects_with_limits", ("telemetry", "anomaly", "triage", "false_positive")),
    _bridge("logic_proof", "cryptography_protocol_security", "verifies", ("invariant", "state", "authentication", "replay")),
    _bridge("embedded_systems", "hardware_embedded_ot_security", "hardens", ("firmware", "interface", "update", "safety")),
    _bridge("law_regulation_ethics", "security_research_disclosure", "authorizes", ("scope", "minimal_proof", "embargo", "disclosure")),
    _bridge("detection_threat_hunting_incident_response", "security_architecture_operations", "improves", ("incident", "control", "metric", "continuity")),
    _bridge("earth_climate", "uncrewed_aerial_systems", "sets_environment", ("wind", "rain", "terrain", "visibility")),
    _bridge("precision_agriculture", "uncrewed_aerial_systems", "applies", ("remote_sensing", "field_route", "crop_action")),
    _bridge("agronomy_soil", "precision_agriculture", "defines_biological_objective", ("soil", "crop_stress", "yield")),
    _bridge("sensors_instrumentation", "precision_agriculture", "measures", ("spectra", "moisture", "position", "calibration")),
    _bridge("energy_storage", "generation_grids", "balances", ("state_of_charge", "demand", "resilience")),
    _bridge("discrete_optimization", "generation_grids", "schedules", ("dispatch", "capacity", "constraints")),
    _bridge("economics_core", "energy_policy_sustainability", "values_tradeoffs", ("externality", "incentive", "market")),
    _bridge("accounting_corporate_finance", "manufacturing_quality", "prices", ("unit_cost", "capital", "scrap", "warranty")),
    _bridge("data_databases", "business_strategy_operations", "informs", ("metrics", "truth_source", "forecast")),
    _bridge("data_science_ml", "marketing_sales_customer", "predicts_with_limits", ("segment", "attribution", "retention", "bias")),
    _bridge("psychology_organisations", "human_computer_interaction", "grounds", ("attention", "mental_model", "error")),
    _bridge("scientific_method", "business_strategy_operations", "tests", ("hypothesis", "experiment", "causal_effect")),
    _bridge("software_engineering", "embedded_systems", "extends_into_hardware", ("requirements", "testing", "reliability")),
    _bridge("systems_engineering", "business_strategy_operations", "connects_delivery_to_value", ("requirement", "risk", "lifecycle_cost")),
    _bridge("ecology_microbiology", "water_waste_resilience", "constrains", ("ecosystem", "contamination", "recovery")),
    _bridge("physiology_health", "data_science_ml", "uses_with_clinical_limits", ("outcome", "bias", "uncertainty", "safety")),
    _bridge("markets_investing", "data_science_ml", "uses_with_financial_limits", ("time_series", "risk", "regime_change", "uncertainty")),
    _bridge("probability_statistics", "financial_mathematics", "grounds", ("conditional_expectation", "distribution", "uncertainty", "tail")),
    _bridge("stochastic_processes_finance", "derivatives_structured_products", "prices_and_hedges", ("path", "measure", "volatility", "sensitivity")),
    _bridge("financial_econometrics", "quantitative_research", "tests", ("stationarity", "leakage", "regime", "out_of_sample_error")),
    _bridge("data_science_ml", "quantitative_research", "supplies_models_with_limits", ("features", "validation", "overfitting", "interpretability")),
    _bridge("discrete_optimization", "portfolio_construction", "allocates_under_constraints", ("objective", "constraint", "turnover", "risk_budget")),
    _bridge("market_microstructure_execution", "systematic_trading", "turns_signal_into_realised_return", ("impact", "latency", "liquidity", "slippage")),
    _bridge("financial_risk_management", "hedge_fund_operations", "governs_survival", ("leverage", "liquidity", "counterparty", "drawdown")),
    _bridge("accounting_corporate_finance", "fundamental_equity_credit", "supplies_economic_evidence", ("earnings", "cash_flow", "balance_sheet", "capital_structure")),
    _bridge("financial_regulation_compliance", "systematic_trading", "constrains", ("market_abuse", "best_execution", "audit", "jurisdiction")),
    _bridge("software_engineering", "quantitative_research", "makes_reproducible", ("versioning", "testing", "data_lineage", "deployment")),
    _bridge("data_databases", "financial_data_infrastructure", "grounds", ("lineage", "point_in_time", "quality", "reproducibility")),
    _bridge("probability_statistics", "probabilistic_forecasting_calibration", "calibrates", ("base_rate", "update", "score", "uncertainty")),
    _bridge("probabilistic_forecasting_calibration", "prediction_market_microstructure", "turns_belief_into_price", ("probability", "edge", "fee", "threshold")),
    _bridge("financial_data_infrastructure", "prediction_market_microstructure", "supplies_point_in_time_books", ("quote", "timestamp", "liquidity", "lineage")),
    _bridge("event_evidence_resolution_research", "probabilistic_forecasting_calibration", "supplies_verifiable_evidence", ("source", "timeline", "resolution", "conflict")),
    _bridge("elections_polling_public_opinion", "event_evidence_resolution_research", "specialises", ("poll", "turnout", "institution", "scenario")),
    _bridge("psychology_organisations", "prediction_market_microstructure", "models_bias_without_assuming_it", ("crowd", "herding", "overconfidence", "adversarial_test")),
    _bridge("law_regulation_ethics", "prediction_market_design_compliance", "authorizes", ("jurisdiction", "integrity", "disclosure", "approval")),
    _bridge("financial_risk_management", "institutional_banking_treasury", "governs", ("liquidity", "funding", "stress", "limits")),
    _bridge("portfolio_construction", "alternative_private_markets", "allocates", ("illiquidity", "capacity", "valuation", "due_diligence")),
    _bridge("law_regulation_ethics", "tax_wealth_structuring", "constrains", ("jurisdiction", "conduct", "referral", "documentation")),
    _bridge("negotiation_governance", "power_institutions_legitimacy", "governs", ("authority", "accountability", "trust", "legitimacy")),
    _bridge("language_research_communication", "information_intelligence_attention", "interprets", ("source", "uncertainty", "narrative", "transparency")),
    _bridge("accounting_corporate_finance", "strategic_assets_capital_allocation", "values", ("cash_flow", "capital", "control", "exit")),
    _bridge("power_institutions_legitimacy", "strategic_assets_capital_allocation", "constrains", ("legitimacy", "law", "stakeholders", "governance")),
    _bridge("systems_engineering", "technology_industry_platforms", "scales", ("architecture", "standard", "lifecycle", "dependency")),
    _bridge("psychology_organisations", "networks_talent_coordination", "grounds", ("incentive", "culture", "team", "succession")),
    _bridge("history_geography_geopolitics", "resilience_geography_long_horizon", "contextualises", ("geography", "trade", "resource", "scenario")),
    _bridge("financial_risk_management", "resilience_geography_long_horizon", "stress_tests", ("concentration", "liquidity", "scenario", "survival")),
    _bridge("history_geography_geopolitics", "supply_chain_procurement", "explains_risk_context", ("trade", "jurisdiction", "disruption")),
    _bridge("design_creative_practice", "manufacturing_quality", "converts_concept_to_product", ("form", "material", "process", "cost")),
)


CAPSTONES = (
    {"project_id": "safe_search_rescue_drone", "objective": "Design and simulate a low-cost, lawful search-and-rescue drone under endurance, payload, weather, privacy, reliability and unit-cost constraints.", "subjects": ("uncrewed_aerial_systems", "energy_storage", "control_robotics", "embedded_systems", "manufacturing_quality", "discrete_optimization", "law_regulation_ethics"), "authorities": ("physics_simulation", "energy_ledger", "control_tests", "cost_model", "safety_and_regulatory_review")},
    {"project_id": "precision_farm_system", "objective": "Design a measured precision-farming system that improves resource use without overstating biological outcomes.", "subjects": ("agronomy_soil", "precision_agriculture", "sensors_instrumentation", "data_science_ml", "uncrewed_aerial_systems", "economics_core"), "authorities": ("withheld_field_data", "agronomy_review", "uncertainty_audit", "cost_outcome")},
    {"project_id": "resilient_microgrid", "objective": "Optimise a safe microgrid across generation, storage, demand, reliability, emissions and lifetime cost.", "subjects": ("generation_grids", "energy_storage", "discrete_optimization", "energy_policy_sustainability", "electronics_circuits", "accounting_corporate_finance"), "authorities": ("power_flow_simulation", "fault_tests", "cost_model", "policy_constraints")},
    {"project_id": "adaptive_factory", "objective": "Improve a small factory using sensing, quality control, automation, maintenance and unit economics.", "subjects": ("manufacturing_quality", "control_robotics", "sensors_instrumentation", "data_science_ml", "supply_chain_procurement", "accounting_corporate_finance"), "authorities": ("process_simulation", "quality_metrics", "downtime_outcome", "financial_ledger")},
    {"project_id": "governed_business_automation", "objective": "Build a governed business operating system that converts verified evidence into useful, approval-gated departmental work.", "subjects": ("business_strategy_operations", "accounting_corporate_finance", "software_engineering", "data_databases", "data_science_ml", "human_computer_interaction", "law_regulation_ethics", "cybersecurity"), "authorities": ("real_user_outcomes", "accounting_reconciliation", "security_tests", "human_approval")},
    {"project_id": "water_resilience", "objective": "Design a monitored water-conservation and failure-response plan for a resource-constrained community.", "subjects": ("water_waste_resilience", "earth_climate", "sensors_instrumentation", "discrete_optimization", "economics_core", "negotiation_governance"), "authorities": ("hydrology_model", "sensor_data", "cost_envelope", "stakeholder_review")},
    {"project_id": "governed_quantitative_fund", "objective": "Research, paper-trade and govern a multi-strategy quantitative portfolio under realistic costs, capacity, liquidity, model-risk, compliance and drawdown constraints.", "subjects": ("probability_statistics", "quantitative_research", "systematic_trading", "portfolio_construction", "financial_risk_management", "market_microstructure_execution", "accounting_corporate_finance", "software_engineering", "data_science_ml", "financial_regulation_compliance", "psychology_organisations"), "authorities": ("frozen_market_data", "delayed_paper_outcomes", "independent_risk_recalculation", "cost_and_slippage_ledger", "compliance_review")},
    {"project_id": "governed_strategic_asset_portfolio", "objective": "Map an industry, identify lawful bottlenecks and dependencies, rank build-buy-partner options, and propose a resilient strategic-asset portfolio without moving capital or exercising external authority.", "subjects": ("strategic_assets_capital_allocation", "power_institutions_legitimacy", "information_intelligence_attention", "technology_industry_platforms", "networks_talent_coordination", "resilience_geography_long_horizon", "financial_risk_management", "cybersecurity", "energy_fundamentals"), "authorities": ("public_filings_and_asset_registers", "independent_valuation", "legal_and_competition_review", "stakeholder_harm_review", "owner_approval", "later_operating_outcomes")},
    {"project_id": "owned_purple_team_cyber_range", "objective": "Assess an explicitly owned isolated network and application range, demonstrate bounded weaknesses, detect the activity, repair every validated defect and independently prove the repaired range resists the same and variant attacks.", "subjects": ("application_web_api_security", "network_wireless_security", "cloud_identity_container_security", "adversary_emulation_penetration_testing", "exploit_analysis_reverse_engineering", "detection_threat_hunting_incident_response", "cryptography_protocol_security", "hardware_embedded_ot_security", "security_research_disclosure", "security_architecture_operations", "law_regulation_ethics", "probability_statistics", "business_strategy_operations"), "authorities": ("signed_scope_manifest", "isolated_range_receipt", "frozen_vulnerable_baseline", "attack_and_detection_ledger", "patched_regression_suite", "independent_retest", "zero_external_targets")},
    {"project_id": "governed_prediction_market_fund", "objective": "Continuously ingest real public prediction markets, research resolvable events, commit calibrated probabilities before outcomes, paper-trade under realistic fees and liquidity, learn from delayed settlement, and only after independent evidence propose tightly bounded owner-approved live orders and compliant market suggestions.", "subjects": ("probabilistic_forecasting_calibration", "prediction_market_microstructure", "event_evidence_resolution_research", "elections_polling_public_opinion", "prediction_market_design_compliance", "financial_risk_management", "financial_regulation_compliance", "psychology_organisations", "history_geography_geopolitics", "data_science_ml", "software_engineering"), "authorities": ("live_public_orderbooks", "frozen_point_in_time_forecasts", "later_platform_settlements", "independent_brier_and_pnl_recalculation", "jurisdiction_and_account_eligibility", "owner_signed_loss_budget", "human_approval_per_live_order", "zero_live_capital_during_qualification")},
)


PHASES = (
    {"phase": 0, "name": "learn_to_learn", "exit": "all learning capabilities pass bounded source-disjoint tests"},
    {"phase": 1, "name": "foundational_literacy", "exit": "logic, mathematics, communication, scientific method, computing and safety are functional"},
    {"phase": 2, "name": "broad_domain_foundations", "exit": "every domain has assessed foundations and an explicit uncertainty map"},
    {"phase": 3, "name": "deep_subject_expertise", "exit": "selected subjects meet expert evidence gates; no claim from curriculum completion alone"},
    {"phase": 4, "name": "cross_domain_capstones", "exit": "multi-domain projects beat subject-isolated controls under independent outcomes"},
    {"phase": 5, "name": "professional_apprenticeship", "exit": "unfamiliar real projects, specialist review and 90-day retention pass"},
    {"phase": 6, "name": "frontier_research", "exit": "novel claims survive literature search, adversarial attack, replication and external scrutiny"},
)


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _subject_map() -> dict[str, dict[str, Any]]:
    return {row["subject_id"]: dict(row) for row in SUBJECTS}


def validate_curriculum(payload: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    subjects = payload.get("subjects") or {}
    capabilities = payload.get("learning_capabilities") or {}
    bridges = payload.get("cross_domain_bridges") or []
    required_caps = {row["capability_id"] for row in LEARNING_CAPABILITIES}
    if set(capabilities) != required_caps:
        errors.append("LEARNING_CAPABILITY_SET_INCOMPLETE")
    for subject_id, row in subjects.items():
        if len(row.get("competencies") or []) < 5:
            errors.append(f"SUBJECT_TOO_SHALLOW:{subject_id}")
        if not row.get("expert_gate", {}).get("independent_authority_required"):
            errors.append(f"SUBJECT_SELF_CERTIFIES:{subject_id}")
        for prerequisite in row.get("prerequisites") or []:
            if prerequisite not in subjects:
                errors.append(f"UNKNOWN_PREREQUISITE:{subject_id}:{prerequisite}")
    indegree = {subject_id: 0 for subject_id in subjects}
    children: dict[str, list[str]] = defaultdict(list)
    for subject_id, row in subjects.items():
        for prerequisite in row.get("prerequisites") or []:
            children[prerequisite].append(subject_id)
            indegree[subject_id] += 1
    queue = deque(sorted(key for key, value in indegree.items() if value == 0))
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for child in children[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if visited != len(subjects):
        errors.append("PREREQUISITE_GRAPH_HAS_CYCLE")
    domains = {row["domain"] for row in subjects.values()}
    bridged_domains: set[str] = set()
    for bridge in bridges:
        if bridge.get("source") not in subjects or bridge.get("target") not in subjects:
            errors.append(f"BRIDGE_HAS_UNKNOWN_NODE:{bridge.get('bridge_id')}")
            continue
        bridged_domains.add(subjects[bridge["source"]]["domain"])
        bridged_domains.add(subjects[bridge["target"]]["domain"])
    if bridged_domains != domains:
        errors.append("NOT_EVERY_DOMAIN_PARTICIPATES_IN_CROSS_DOMAIN_GRAPH")
    for project in payload.get("capstones") or []:
        project_domains = {subjects[item]["domain"] for item in project["subjects"]}
        if len(project_domains) < 4:
            errors.append(f"CAPSTONE_NOT_CROSS_DOMAIN:{project['project_id']}")
        if len(project.get("authorities") or []) < 3:
            errors.append(f"CAPSTONE_UNDER_VERIFIED:{project['project_id']}")
    safety = payload.get("governance") or {}
    if not safety.get("dual_use_restrictions") or not safety.get("high_stakes_escalation"):
        errors.append("SAFETY_GOVERNANCE_INCOMPLETE")
    return {
        "valid": not errors,
        "errors": errors,
        "learning_capabilities": len(capabilities),
        "subjects": len(subjects),
        "domains": len(domains),
        "bridges": len(bridges),
        "capstones": len(payload.get("capstones") or []),
        "prerequisite_graph_acyclic": "PREREQUISITE_GRAPH_HAS_CYCLE" not in errors,
        "all_domains_bridged": "NOT_EVERY_DOMAIN_PARTICIPATES_IN_CROSS_DOMAIN_GRAPH" not in errors,
    }


def build_curriculum() -> dict[str, Any]:
    subjects = _subject_map()
    capabilities = {row["capability_id"]: dict(row) for row in LEARNING_CAPABILITIES}
    domains: dict[str, list[str]] = defaultdict(list)
    for subject_id, row in subjects.items():
        domains[row["domain"]].append(subject_id)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA,
        "created_at": _utc_timestamp(),
        "purpose": (
            "Accumulate deep, evidence-backed subject expertise and verified cross-domain "
            "synthesis while preserving uncertainty, safety, human authority and real-world grounding."
        ),
        "mastery_levels": list(LEVELS),
        "learning_capabilities": capabilities,
        "subjects": subjects,
        "domains": {key: sorted(value) for key, value in sorted(domains.items())},
        "cross_domain_bridges": [dict(row) for row in CROSS_DOMAIN_BRIDGES],
        "capstones": [dict(row) | {"subjects": list(row["subjects"]), "authorities": list(row["authorities"])} for row in CAPSTONES],
        "phases": [dict(row) for row in PHASES],
        "knowledge_graph": {
            "node_types": ["concept", "claim", "equation", "procedure", "model", "component", "constraint", "measurement", "failure", "question", "source", "authority"],
            "edge_types": ["prerequisite", "part_of", "causes", "constrains", "implements", "measures", "optimizes", "analogous_to", "contradicts", "supports", "regulated_by", "manufactured_by", "transfers_to"],
            "required_fields": ["provenance", "confidence", "valid_scope", "counterexamples", "last_verified", "retention_status"],
            "unknown_policy": "unknowns and contradictions remain first-class nodes rather than being silently completed",
        },
        "scheduler": {
            "bootstrapping_allocation": {"learning_capabilities": 30, "foundations": 35, "subject_depth": 15, "cross_domain_projects": 10, "retention_repair": 10},
            "mature_allocation": {"subject_depth": 30, "cross_domain_projects": 25, "frontier_research": 15, "retention_repair": 20, "breadth_discovery": 10},
            "selection_score": ["mission_relevance", "knowledge_graph_centrality", "weakness", "expected_transfer_value", "evidence_availability", "risk", "cost"],
            "parallel_lanes": ["immediate_problem", "broad_subject_academy", "cross_domain_synthesis", "retention", "frontier_questions"],
        },
        "assessment_protocol": {
            "teacher_is_proposal_only": True,
            "exam_is_source_disjoint": True,
            "self_scoring_cannot_award_competence": True,
            "controls": ["cold", "no_memory", "no_repair", "subject_isolated"],
            "retention_days": [1, 7, 30, 90],
            "expert_requires_real_outcomes": True,
            "research_requires_replication_and_external_scrutiny": True,
        },
        "governance": {
            "dual_use_restrictions": "permit benign, defensive, safety, resilience and compliance work; block weapon construction, targeting and harmful operational enablement",
            "high_stakes_escalation": "medical, legal and financial actions require current authoritative sources and qualified human authority",
            "physical_execution": "requires authorised hardware, sandbox, safety case and human approval",
            "claim_boundary": "curriculum membership, reading and practice never constitute expertise",
        },
        "expansion_protocol": {
            "trigger": ["new_problem", "unmapped_term", "failed_transfer", "contradictory_evidence", "new_discovery", "stale_knowledge"],
            "steps": ["diagnose_gap", "map_prerequisites", "acquire_sources", "learn_and_practise", "independent_exam", "create_graph_nodes", "discover_bridges", "delayed_retest"],
            "no_finite_syllabus_stop": True,
        },
    }
    validation = validate_curriculum(payload)
    payload["validation"] = validation
    # Identity follows curriculum content, not the wall-clock time at which an
    # equivalent artifact was rendered.
    payload["curriculum_digest"] = _canonical_hash(
        {key: value for key, value in payload.items() if key != "created_at"}
    )
    return payload


def select_portfolio(curriculum: Mapping[str, Any], problem: str, *, limit: int = 30) -> dict[str, Any]:
    subjects = curriculum["subjects"]
    lowered = problem.lower()
    tokens = {part.strip(".,:;!?()[]{}") for part in lowered.split()}

    def mentioned(keyword: str) -> bool:
        return keyword in lowered if " " in keyword else keyword in tokens

    scores = {
        subject_id: sum(mentioned(keyword) for keyword in row.get("keywords") or [])
        for subject_id, row in subjects.items()
    }
    seeds = [subject_id for subject_id in sorted(scores, key=lambda key: (-scores[key], key)) if scores[subject_id] > 0][:10]
    # Preserve every directly relevant subject before expanding prerequisites;
    # otherwise one deep prerequisite chain can crowd out another explicit
    # requirement such as law, cost or safety.
    selected: list[str] = list(seeds)

    def add_with_prerequisites(subject_id: str) -> None:
        for prerequisite in subjects[subject_id].get("prerequisites") or []:
            if prerequisite not in selected and len(selected) < limit:
                add_with_prerequisites(prerequisite)
        if subject_id not in selected and len(selected) < limit:
            selected.append(subject_id)

    for seed in seeds:
        for prerequisite in subjects[seed].get("prerequisites") or []:
            add_with_prerequisites(prerequisite)
    bridge_candidates = []
    for bridge in curriculum["cross_domain_bridges"]:
        if bridge["source"] in selected or bridge["target"] in selected:
            other = bridge["target"] if bridge["source"] in selected else bridge["source"]
            bridge_candidates.append((other, bridge))
    for other, _ in bridge_candidates:
        if len(selected) >= limit:
            break
        add_with_prerequisites(other)
    domains = sorted({subjects[item]["domain"] for item in selected})
    used_bridges = [row for row in curriculum["cross_domain_bridges"] if row["source"] in selected and row["target"] in selected]
    return {
        "problem": problem,
        "seed_subjects": seeds,
        "selected_subjects": selected,
        "domains": domains,
        "bridges": [row["bridge_id"] for row in used_bridges],
        "cross_domain": len(domains) >= 3,
        "portfolio_digest": _canonical_hash([problem, selected, [row["bridge_id"] for row in used_bridges]]),
    }


def run_comprehensive_expertise_curriculum_phase(*, curriculum_path: Path, result_path: Path | None = None) -> dict[str, Any]:
    curriculum = build_curriculum()
    if not curriculum["validation"]["valid"]:
        raise ValueError(curriculum["validation"]["errors"])
    _atomic(curriculum_path, curriculum)
    scenarios = {
        "drone": select_portfolio(curriculum, "Design a safe cheap intelligent search-and-rescue drone with long battery endurance, payload navigation, embedded software, manufacture and legal operation."),
        "farm": select_portfolio(curriculum, "Improve crop yield and water use on a farm using soil science, sensors, drone mapping, data and economics."),
        "business": select_portfolio(curriculum, "Build governed business software that connects finance, operations, customers, databases, AI, security and human approval."),
    }
    gate = {
        **curriculum["validation"],
        "scenario_count": len(scenarios),
        "all_scenarios_cross_domain": all(row["cross_domain"] for row in scenarios.values()),
        "drone_spans_at_least_five_domains": len(scenarios["drone"]["domains"]) >= 5,
        "no_competence_awarded": True,
        "paid_api_calls": 0,
        "unsafe_actions": 0,
    }
    gate["accepted"] = bool(
        gate["valid"]
        and gate["all_scenarios_cross_domain"]
        and gate["drone_spans_at_least_five_domains"]
        and gate["no_competence_awarded"]
        and gate["paid_api_calls"] == gate["unsafe_actions"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.comprehensive_expertise_curriculum_phase_result.v1",
        "created_at": _utc_timestamp(),
        "passed": gate["accepted"],
        "curriculum_path": str(curriculum_path),
        "curriculum_digest": curriculum["curriculum_digest"],
        "scenarios": scenarios,
        "gate": gate,
        "claim_boundary": (
            "This phase defines and validates an executable curriculum and cross-domain graph. "
            "It does not establish that AION has learned the listed subjects. Expertise is awarded "
            "only after source-disjoint exams, real projects, independent outcomes and delayed retention."
        ),
    }
    result["result_digest"] = _canonical_hash(result)
    if result_path is not None:
        _atomic(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the comprehensive AION expertise curriculum.")
    parser.add_argument("--curriculum-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_comprehensive_expertise_curriculum_phase(curriculum_path=args.curriculum_path, result_path=args.result_path), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
