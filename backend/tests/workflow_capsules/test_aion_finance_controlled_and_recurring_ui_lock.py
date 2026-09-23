from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BRIDGE = (ROOT / "desktop/mac/src/aion_department_pilot_backend.js").read_text(encoding="utf-8")
SCHEDULER = (ROOT / "backend/tasks/scheduler.py").read_text(encoding="utf-8")


def test_finance_queue_exposes_exact_payload_approval_without_live_execute_button():
    assert "Controlled Finance proposal" in BRIDGE
    assert "Exact payload hash" in BRIDGE
    assert "Approve exact payload" in BRIDGE
    assert "decideFinanceProposal" in BRIDGE
    assert "data-payload-hash" in BRIDGE
    assert "execute-live-finance-proposal" not in BRIDGE


def test_finance_recurring_panel_exposes_all_read_only_schedule_types_and_failure_state():
    for kind in (
        "weekly_cash_update", "monthly_management_report", "period_close_check",
        "exception_cash_buffer_alert",
    ):
        assert kind in BRIDGE
    assert "Finance / Recurring" in BRIDGE
    assert "failure_count" in BRIDGE
    assert "runFinanceRecurring" in BRIDGE
    assert "setFinanceRecurringEnabled" in BRIDGE


def test_failed_department_task_has_safe_retry_control():
    assert "data-aion-department-task-retry" in BRIDGE
    assert "retryDepartmentTask" in BRIDGE
    assert "no external action taken" in BRIDGE


def test_process_scheduler_owns_due_scan_without_duplicate_instances():
    assert "run_finance_recurring_work" in SCHEDULER
    assert 'id="aion-finance-recurring-work"' in SCHEDULER
    assert "max_instances=1" in SCHEDULER
    assert "coalesce=True" in SCHEDULER
