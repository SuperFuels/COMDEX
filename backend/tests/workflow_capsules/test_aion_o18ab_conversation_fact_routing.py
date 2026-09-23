from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
OPERATING_MODEL = (ROOT / "desktop/mac/src/aion_operating_model_workspace.js").read_text(encoding="utf-8")
OPERATING_MODEL_API = (ROOT / "backend/modules/aion_business/api/business_twin_data_api.py").read_text(encoding="utf-8")


def test_all_six_department_question_sets_have_governed_routes():
    assert "const DISCOVERY_ROUTES =" in APP
    routes = APP.split("const DISCOVERY_ROUTES =", 1)[1].split("function extractStructuredAnswerO18AB", 1)[0]
    for department in ("marketing", "sales", "finance", "operations", "support", "hr"):
        block = routes.split(f"    {department}: [", 1)[1].split("    ],", 1)[0]
        assert block.count("[") == 6
    assert '["engineer_planning_rate", "products_services", "workforce"' in APP
    assert '["target_gross_margin", "products_services", "summary"' in APP


def test_pilot_answers_update_boardroom_department_and_owning_workspace():
    assert "function routeDepartmentPilotAnswerO18AB" in APP
    assert "window.updateAionDepartmentIntelligence?.(key" in APP
    assert 'aion.boardroom.discovery_answers.v1' in APP
    assert "window.AionOperatingModelWorkspace?.applyConversationFact?.(fact)" in APP
    assert "Saved to ${targetLabel} and Boardroom context." in APP
    assert "answers[field].route_receipt = routeReceipt" in APP


def test_boardroom_answers_use_the_same_router():
    assert "window.aionRouteBoardroomDiscoveryAnswerO18AB" in APP
    assert "inferBoardroomDiscoveryRouteO18AB" in APP
    assert "window.aionRouteBoardroomDiscoveryAnswerO18AB(entry)" in APP


def test_operating_model_persists_and_displays_conversation_facts():
    assert "function applyConversationFact" in OPERATING_MODEL
    assert "persistConversationFactsToBackend" in OPERATING_MODEL
    assert "conversation_facts" in OPERATING_MODEL
    assert "Captured by your AION agents" in OPERATING_MODEL
    assert "renderedConversationFacts('workforce')" in OPERATING_MODEL
    assert "renderedConversationFacts('offerings')" in OPERATING_MODEL
    assert "renderedConversationFacts('jobs')" in OPERATING_MODEL
    assert "renderedConversationFacts('summary')" in OPERATING_MODEL
    assert "applyConversationFact, state" in OPERATING_MODEL


def test_department_conversation_uses_light_visual_system():
    start = APP.index("function ensureStyleO18AA")
    end = APP.index("function escO18AA", start)
    style = APP[start:end]
    assert "background:#f7fafc" in style
    assert "background:#edf8fc" in style
    assert "background:#ffffff" in style
    assert "background:#1267d6" in style
    assert "height:42px" in style


def test_pilot_reuses_canonical_business_records_before_agent_question_planning():
    assert "function canonicalAnswerO18AB" in APP
    assert "function hydrateCanonicalAnswersO18AB" in APP
    assert "model.labour_resources" in APP
    assert 'source: "canonical_business_record"' in APP
    assert "function requestNextDiscoveryQuestionO18AC" in APP
    assert "/discovery/next-question" in APP
    assert "Existing business records reused" in APP
    assert "no fixed questionnaire" in APP


def test_workforce_planning_rate_is_editable_and_basis_aware():
    assert "function planningRateFromHR" in OPERATING_MODEL
    assert "function syncLabourPlanningRate" in OPERATING_MODEL
    assert "Editable planning rate" in OPERATING_MODEL
    assert "manual_planning_override" in OPERATING_MODEL
    assert "basis_changed" in OPERATING_MODEL
    assert "confidential pay in HR is never changed" in OPERATING_MODEL


def test_manual_planning_override_survives_backend_save():
    assert 'str(resource.get("rate_source") or "") == "manual_planning_override"' in OPERATING_MODEL_API
    assert 'cost_source = "owner_planning_override"' in OPERATING_MODEL_API
    assert 'effective_rate = resource.get("cost_rate")' in OPERATING_MODEL_API


def test_department_questions_are_generated_by_the_pilot_not_hardwired_in_the_ui():
    assert "discoveryPlannerStateO18AC" in APP
    assert "requestNextDiscoveryQuestionO18AC" in APP
    assert "Question source:" in APP
    assert 'questions: []' in APP
    assert "engineer hourly or daily cost" not in APP[APP.index("finance: {"):APP.index("operations: {")]


def test_discovery_questions_can_be_skipped_without_inventing_a_fact():
    assert 'data-aion-o18aa-skip="${safeKey}"' in APP
    assert "function skipCurrentQuestionO18AA" in APP
    assert "function recordDiscoveryGapO18AB" in APP
    assert 'status: "evidence_required"' in APP
    assert 'source: "owner_deferred"' in APP
    assert "No value was invented or saved as fact." in APP
    assert "existing.skipped !== true" in APP
