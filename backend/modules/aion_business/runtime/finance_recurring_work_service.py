"""Persistent read-only recurring Finance work and run state."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import calendar
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_management_report_builder import build_finance_management_report
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


KINDS = {"weekly_cash_update", "monthly_management_report", "period_close_check", "exception_cash_buffer_alert"}


def _now() -> str: return datetime.now(UTC).replace(microsecond=0).isoformat()
def _safe(value: str) -> str: return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")
def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00")); return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _next_run(value: str, cadence: str) -> str:
    current = _parse(value)
    if cadence == "daily": return (current + timedelta(days=1)).isoformat()
    if cadence == "weekly": return (current + timedelta(days=7)).isoformat()
    year, month = current.year, current.month + 1
    if month == 13: year, month = year + 1, 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return current.replace(year=year, month=month, day=day).isoformat()


class FinanceRecurringWorkService:
    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()

    def create(self, workspace_id: str, *, schedule_id: str, kind: str, cadence: str,
               next_run_at: str, created_by: str, minimum_cash_reserve: float = 0) -> dict[str, Any]:
        if kind not in KINDS: raise ValueError("unsupported_finance_schedule_kind")
        expected = {"weekly_cash_update": "weekly", "monthly_management_report": "monthly", "period_close_check": "monthly", "exception_cash_buffer_alert": "daily"}[kind]
        if cadence != expected: raise ValueError(f"finance_schedule_cadence_must_be:{expected}")
        record = {"schema_version": "aion.finance_pilot.schedule.v1", "schedule_id": _safe(schedule_id),
                  "workspace_id": workspace_id, "kind": kind, "cadence": cadence, "enabled": True,
                  "minimum_cash_reserve": max(0, float(minimum_cash_reserve)), "created_by": created_by,
                  "created_at": _now(), "next_run_at": _parse(next_run_at).isoformat(), "last_run_at": None,
                  "last_run_status": "never_run", "last_error": None, "failure_count": 0, "run_count": 0}
        record["schedule_hash"] = canonical_contract_hash(record)
        path = self._schedule_path(workspace_id, record["schedule_id"])
        if path.exists(): raise FileExistsError(f"Finance schedule already exists: {record['schedule_id']}")
        self._write(path, record); return record

    def list(self, workspace_id: str) -> list[dict[str, Any]]:
        records = []
        for path in sorted(self._dir(workspace_id).glob("*/schedule.json")):
            record = json.loads(path.read_text()); self._verify(record); records.append(record)
        return records

    def set_enabled(self, workspace_id: str, schedule_id: str, enabled: bool) -> dict[str, Any]:
        record, path = self._load(workspace_id, schedule_id); record["enabled"] = bool(enabled)
        record.pop("schedule_hash", None); record["schedule_hash"] = canonical_contract_hash(record); self._write(path, record); return record

    def run(self, workspace_id: str, schedule_id: str, *, run_at: str | None = None,
            actor_id: str = "finance_scheduler") -> dict[str, Any]:
        occurred_at = run_at or _now(); schedule, path = self._load(workspace_id, schedule_id)
        if not schedule["enabled"]: raise ValueError("finance_schedule_disabled")
        try:
            financial = self.repository.load_dict(workspace_id, "business_financial_model")
            management = build_finance_management_report(financial, generated_at=occurred_at)
            headline = management["headline"]; cash = headline.get("ending_cash")
            if schedule["kind"] == "weekly_cash_update": result = {"cash": cash, "freshness": management["evidence_freshness"], "warnings": management["warnings"]}
            elif schedule["kind"] == "monthly_management_report": result = {"period": management["period"], "headline": headline, "kpis": management["kpis"], "warnings": management["warnings"]}
            elif schedule["kind"] == "period_close_check": result = {"ready": not management["missing_core_metrics"] and not management["warnings"], "missing_core_metrics": management["missing_core_metrics"], "warnings": management["warnings"]}
            else:
                reserve = schedule["minimum_cash_reserve"]
                result = {"cash": cash, "minimum_cash_reserve": reserve, "alert": cash is None or cash < reserve, "warnings": management["warnings"]}
            run = {"schema_version": "aion.finance_pilot.schedule_run.v1", "run_id": _safe(f"{schedule_id}-{occurred_at}"), "schedule_id": schedule_id, "workspace_id": workspace_id, "kind": schedule["kind"], "status": "completed", "run_at": occurred_at, "actor_id": actor_id, "result": result, "external_action_performed": False}
            run["run_hash"] = canonical_contract_hash(run); self._write(self._run_path(workspace_id, schedule_id, run["run_id"]), run)
            schedule.update({"last_run_at": occurred_at, "last_run_status": "completed", "last_error": None, "run_count": int(schedule["run_count"]) + 1, "next_run_at": _next_run(occurred_at, schedule["cadence"])})
            self._save_schedule(path, schedule)
            self._project(workspace_id, schedule, run)
            pointer = self._register_pointer(workspace_id, schedule, run)
            return {"schedule": schedule, "run": run, "file_cabinet_pointer": pointer}
        except Exception as exc:
            schedule.update({"last_run_at": occurred_at, "last_run_status": "failed", "last_error": str(exc)[:1000], "failure_count": int(schedule["failure_count"]) + 1, "next_run_at": _next_run(occurred_at, schedule["cadence"])})
            self._save_schedule(path, schedule)
            failure = {
                "schema_version": "aion.finance_pilot.schedule_run.v1",
                "run_id": _safe(f"{schedule_id}-{occurred_at}-failed"),
                "schedule_id": schedule_id,
                "workspace_id": workspace_id,
                "kind": schedule["kind"],
                "status": "failed",
                "run_at": occurred_at,
                "actor_id": actor_id,
                "error": {"type": type(exc).__name__, "message": str(exc)[:1000]},
                "external_action_performed": False,
            }
            failure["run_hash"] = canonical_contract_hash(failure)
            self._write(self._run_path(workspace_id, schedule_id, failure["run_id"]), failure)
            try:
                self._project(workspace_id, schedule, failure)
                self._register_pointer(workspace_id, schedule, failure)
            except Exception:
                pass
            raise

    def run_due(self, workspace_id: str, *, now: str | None = None) -> list[dict[str, Any]]:
        at = now or _now(); current = _parse(at); results = []
        for schedule in self.list(workspace_id):
            if schedule["enabled"] and _parse(schedule["next_run_at"]) <= current:
                try: results.append({"schedule_id": schedule["schedule_id"], "ok": True, **self.run(workspace_id, schedule["schedule_id"], run_at=at)})
                except Exception as exc: results.append({"schedule_id": schedule["schedule_id"], "ok": False, "error": str(exc)})
        return results

    def _dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/recurring"; path.mkdir(parents=True, exist_ok=True); return path
    def _schedule_path(self, workspace_id: str, schedule_id: str) -> Path:
        path = self._dir(workspace_id) / _safe(schedule_id); path.mkdir(parents=True, exist_ok=True); return path / "schedule.json"
    def _run_path(self, workspace_id: str, schedule_id: str, run_id: str) -> Path:
        path = self._schedule_path(workspace_id, schedule_id).parent / "runs"; path.mkdir(exist_ok=True); return path / f"{run_id}.json"
    def _load(self, workspace_id: str, schedule_id: str) -> tuple[dict[str, Any], Path]:
        path = self._schedule_path(workspace_id, schedule_id)
        if not path.exists(): raise FileNotFoundError(f"Finance schedule not found: {schedule_id}")
        record = json.loads(path.read_text()); self._verify(record); return record, path
    @staticmethod
    def _write(path: Path, record: dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp"); temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n"); temporary.replace(path)
    def _save_schedule(self, path: Path, record: dict[str, Any]) -> None:
        record.pop("schedule_hash", None); record["schedule_hash"] = canonical_contract_hash(record); self._write(path, record)
    @staticmethod
    def _verify(record: dict[str, Any]) -> None:
        expected = record.get("schedule_hash"); payload = dict(record); payload.pop("schedule_hash", None)
        if not expected or canonical_contract_hash(payload) != expected: raise ValueError("finance_schedule_hash_mismatch")
    def _project(self, workspace_id: str, schedule: dict[str, Any], run: dict[str, Any]) -> None:
        ledger = self.repository.load_optional_dict(workspace_id, "department_intelligence") or {"id": f"{workspace_id}.department_intelligence", "workspace_id": workspace_id, "kind": "department_intelligence", "meta": {}, "departments": {}, "revision": 1}
        finance = ledger.setdefault("departments", {}).setdefault("finance", {"department": "finance"}); finance.setdefault("recurring_work", {})[schedule["schedule_id"]] = {"schedule": schedule, "latest_run": run}; finance["latest_recurring_run"] = run; ledger["revision"] = int(ledger.get("revision") or 1) + 1; self.repository.save_dict(workspace_id, "department_intelligence", ledger)
        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom is not None: boardroom.setdefault("boardroom", {}).setdefault("runtime", {})["latest_finance_recurring_run"] = run; self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)

    def _register_pointer(self, workspace_id: str, schedule: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
        path = self._run_path(workspace_id, schedule["schedule_id"], run["run_id"])
        tree = WorkflowFileCabinetRepository.load(workspace_id)
        folders = tree.get("folders")
        if not isinstance(folders, list):
            folders = list((tree.get("root") or {}).get("children") or [])
            tree["folders"] = folders

        def ensure(children: list[dict[str, Any]], node_id: str, name: str, node_type: str = "folder") -> dict[str, Any]:
            node = next((item for item in children if item.get("id") == node_id), None)
            if node is None:
                node = {"id": node_id, "name": name, "type": node_type, "children": []}
                children.append(node)
            node.update({"name": name, "type": node_type})
            node.setdefault("children", [])
            return node

        finance = ensure(folders, "folder_finance", "Finance", "department")
        recurring = ensure(finance["children"], "folder_finance_recurring", "Recurring")
        pointer = {
            "id": f"finance_recurring_pointer_{run['run_id']}",
            "name": f"{schedule['kind'].replace('_', ' ').title()} · {run['run_at']}",
            "type": "business_container_artifact",
            "document_type": "finance_recurring_run",
            "source_of_truth": "business_container",
            "file_cabinet_role": "index_pointer_only",
            "status": run["status"],
            "target": {
                "business_container_id": workspace_id,
                "sub_container": "finance",
                "category": "recurring",
                "storage_path": str(path),
                "schedule_id": schedule["schedule_id"],
                "run_id": run["run_id"],
                "run_hash": run["run_hash"],
            },
        }
        index = next((i for i, item in enumerate(recurring["children"]) if item.get("id") == pointer["id"]), None)
        if index is None:
            recurring["children"].append(pointer)
        else:
            recurring["children"][index] = pointer
        tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}
        WorkflowFileCabinetRepository.save(workspace_id, tree)
        return pointer
