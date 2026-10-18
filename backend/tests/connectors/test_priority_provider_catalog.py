from backend.modules.connectors.aion_business_skill_catalog import get_aion_business_skill_catalog
from backend.modules.connectors.priority_provider_catalog import (
    CURRENT_READINESS,
    can_claim_live_verified,
    get_provider_training_syllabus,
    get_priority_provider_catalog,
    validate_priority_provider_catalog,
)
from backend.modules.connectors.provider_release_gate import evaluate_provider_release


def test_all_priority_provider_manifests_are_valid():
    result = validate_priority_provider_catalog()
    assert result["valid"] is True
    assert result["provider_count"] == 16
    assert set(result["providers"]) == {"gmail", "microsoft_outlook", "mailchimp_marketing", "resend", "twilio_messaging", "google_routes", "xero", "quickbooks_online", "sage_accounting", "freeagent", "freshbooks", "zoho_books", "hubspot", "pipedrive", "twilio_voice", "stripe"}
    assert all(len(item["manifest_sha256"]) == 64 for item in result["providers"].values())


def test_priority_catalog_has_atomic_actions_and_financial_limits():
    catalog = get_priority_provider_catalog()
    assert len(catalog["gmail"]["actions"]) >= 4
    assert len(catalog["hubspot"]["actions"]) >= 4
    for action in catalog["stripe"]["actions"]:
        if action["risk"]["financial"]:
            assert action["authority"]["constraints"]["amount_limit_required"] is True
            assert action["authority"]["constraints"]["currency"] == "workspace_policy"


def test_live_claim_requires_every_independent_evidence_gate():
    evidence = {
        "contract_sha256": "a",
        "credential_health_receipt": "b",
        "dry_run_receipt": "c",
        "approved_live_action_receipt": "d",
        "provider_readback_receipt": "e",
        "failure_test_receipt": "f",
        "revocation_test_receipt": "g",
    }
    assert can_claim_live_verified("gmail", evidence) is True
    evidence.pop("provider_readback_receipt")
    assert can_claim_live_verified("gmail", evidence) is False
    assert all(item["stage"] != "live_verified" for item in CURRENT_READINESS.values())


def test_business_skill_catalog_is_large_curated_and_truthful():
    catalog = get_aion_business_skill_catalog()
    ids = [item["skill_id"] for item in catalog["skills"]]
    assert catalog["skill_count"] >= 100
    assert len(ids) == len(set(ids))
    assert {item["stage"] for item in catalog["skills"]} <= {"curriculum_ready", "adapter_linked"}
    assert "not proof of mastery" in catalog["claim_boundary"].lower()


def test_each_priority_provider_has_a_release_curriculum():
    for tool_id in get_priority_provider_catalog():
        syllabus = get_provider_training_syllabus(tool_id)
        assert len(syllabus["lessons"]) >= 7
        assert "retention_and_unfamiliar_transfer" in syllabus["assessments"]


def test_release_gate_fails_closed_until_readback_and_revocation_pass():
    evidence = {"contract_sha256": "contract", "knowledge_assessment_receipt": "knowledge", "adapter_contract_receipt": "adapter", "dry_run_receipt": "dry-run", "credential_health_receipt": "credential", "sandbox_write_receipt": "sandbox", "approved_live_action_receipt": "live-action"}
    report = evaluate_provider_release("gmail", evidence)
    assert report["stage"] == "sandbox_verified"
    assert not report["live_execution_allowed"]
    assert "provider_readback_receipt" in report["missing"]
    evidence.update({"provider_readback_receipt": "readback", "failure_test_receipt": "failure", "revocation_test_receipt": "revocation"})
    report = evaluate_provider_release("gmail", evidence)
    assert report["stage"] == "live_verified"
    assert report["live_execution_allowed"]
