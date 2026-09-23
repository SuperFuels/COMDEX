from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = (ROOT / "desktop/mac/src/aion_hr_people_workspace.js").read_text(encoding="utf-8")
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
SERVICE = (ROOT / "backend/modules/aion_business/runtime/organization_authority_service.py").read_text(encoding="utf-8")


def test_people_workspace_contains_real_operations_ledgers_and_human_gates():
    for marker in ("leave_requests", "appraisals", "escalations", "onboarding_templates"):
        assert marker in SERVICE
        assert marker in WORKSPACE
    assert "human_employment_decisions_required" in SERVICE
    assert "sensitive_detail_excluded_from_dashboard" in SERVICE
    assert "Human authority boundary" in WORKSPACE


def test_people_workspace_supports_leave_review_and_employee_onboarding_evidence():
    for marker in (
        "People operations", "Upcoming absence and cover", "Approval queue",
        "Appraisals and check-ins", "Onboarding readiness", "Restricted issue",
        "Contract signed", "Health & safety", "Software accounts",
        "data-hrw-review-leave", "data-hrw-leave-form",
    ):
        assert marker in WORKSPACE
    assert "Approved by authorised person" in WORKSPACE
    assert "openLeave(leaveId)" in WORKSPACE


def test_people_workspace_read_load_cannot_trigger_an_application_remount_loop():
    visible_render = "if (requireVisibleMount) {\n      render();\n    } else {"
    assert visible_render in WORKSPACE
    assert "if (state.activeTab === \"dashboard\") requestRender?.();" in APP
    assert "if (state.model && state.workspaceId === businessId())" in WORKSPACE
