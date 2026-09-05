from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")
ROUTER = Path("backend/api/workflow_capsule_router.py")


def test_boardroom_workflow_canvas_exposes_stage8_run_and_receipt_surface():
    text = APP_JS.read_text(encoding="utf-8")
    for contract in (
        'data-aion-flow-run-centre="true"',
        "Compile &amp; simulate",
        "Review exact route",
        "Run authorized route",
        "Intelligence Route Receipt",
        "Pause",
        "Resume",
        "Cancel",
        "Recover",
    ):
        assert contract in text


def test_boardroom_stage8_surface_calls_only_governed_backend_routes():
    text = APP_JS.read_text(encoding="utf-8")
    assert "/api/workflow-capsules/aion-flow/prepare" in text
    assert "/api/workflow-capsules/aion-flow/authorize" in text
    assert "/api/workflow-capsules/aion-flow/execute" in text
    assert "/api/workflow-capsules/aion-flow/runs/" in text
    assert "exact_confirmed: true" in text
    assert "review_hash" in text


def test_stage8_api_has_prepare_execute_run_control_and_recovery_routes():
    text = ROUTER.read_text(encoding="utf-8")
    for route in (
        '/aion-flow/prepare',
        '/aion-flow/execute',
        '/aion-flow/runs',
        '/aion-flow/runs/{run_id}',
        '/aion-flow/runs/{run_id}/control',
        '/aion-flow/recover',
    ):
        assert route in text
