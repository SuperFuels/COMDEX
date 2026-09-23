"""Deterministic Finance forecasts and clearly-labelled scenario variants.

Scenario records are separate from historical Finance truth.  Running a scenario
never changes accounting evidence, accepted facts, or an approved task package.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_management_report_builder import build_finance_management_report
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


def _number(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool) or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _month_count(period: dict[str, Any]) -> float:
    basis = str(period.get("basis") or "").lower()
    if basis == "monthly":
        return 1.0
    if basis == "annual":
        return 12.0
    try:
        start = date.fromisoformat(str(period.get("from"))[:10])
        end = date.fromisoformat(str(period.get("to"))[:10])
        return max(1.0, (end - start).days / 30.4375)
    except (TypeError, ValueError):
        pass
    return 1.0


def _ensure_folder(children: list[dict[str, Any]], node_id: str, name: str, node_type: str = "folder") -> dict[str, Any]:
    node = next((item for item in children if item.get("id") == node_id), None)
    if node is None:
        node = {"id": node_id, "name": name, "type": node_type, "children": []}
        children.append(node)
    node.update({"name": name, "type": node_type})
    node.setdefault("children", [])
    return node


class FinanceForecastingService:
    """Create, persist and project read-only Finance scenarios."""

    def __init__(
        self,
        container_repository: BusinessContainerRepository | None = None,
        *,
        artifact_root: Path | None = None,
    ) -> None:
        self.container_repository = container_repository or BusinessContainerRepository()
        self.artifact_root = artifact_root

    def run(
        self,
        workspace_id: str,
        assumptions: dict[str, Any],
        *,
        scenario_name: str = "Finance planning scenario",
        created_by: str = "finance_pilot",
        created_at: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        occurred_at = created_at or _now()
        financial = self.container_repository.load_dict(workspace_id, "business_financial_model")
        management = build_finance_management_report(financial, generated_at=occurred_at)
        normalised = self._normalise_assumptions(assumptions)
        baseline = self._monthly_baseline(management, normalised)
        scenario_id = _safe_id(
            str(assumptions.get("scenario_id") or f"finance-scenario-{occurred_at}")
        )
        variants = {
            "expected": self._variant(baseline, normalised, 0.0),
            "upside": self._variant(baseline, normalised, normalised["sensitivity_percent"]),
            "downside": self._variant(baseline, normalised, -normalised["sensitivity_percent"]),
        }
        record: dict[str, Any] = {
            "schema_version": "aion.finance_pilot.scenario.v1",
            "scenario_id": scenario_id,
            "workspace_id": workspace_id,
            "name": scenario_name.strip() or "Finance planning scenario",
            "status": "modelled_not_actual",
            "created_at": occurred_at,
            "created_by": created_by,
            "currency": management.get("currency") or "EUR",
            "source": {
                "financial_model_revision": financial.get("revision"),
                "financial_model_hash": canonical_contract_hash(financial),
                "management_report_schema": management.get("schema_version"),
                "reporting_period": management.get("period"),
                "evidence_freshness": management.get("evidence_freshness"),
            },
            "assumptions": normalised,
            "calculation_policy": {
                "revenue": "baseline revenue adjusted for revenue, price, volume, sensitivity and annual growth assumptions",
                "direct_costs": "baseline direct costs adjusted for volume, sensitivity and direct-cost assumptions",
                "overheads": "baseline overheads adjusted for overhead assumptions plus monthly hiring cost",
                "cash": "opening cash plus modelled operating profit less the stated one-off stock purchase",
                "excluded": "tax, financing movements, depreciation and working-capital timing are excluded unless already represented in the baseline",
            },
            "monthly_baseline": baseline,
            "variants": variants,
            "warnings": list(dict.fromkeys([
                "This is a planning scenario, not an accounting record or verified forecast.",
                *list(management.get("warnings") or []),
            ]))[:30],
            "external_writes_performed": False,
            "historical_finance_mutated": False,
        }
        record["scenario_hash"] = canonical_contract_hash(record)
        path = self._store(workspace_id, record)
        pointer = self._register_pointer(workspace_id, record, path)
        self._write_intelligence(workspace_id, record, path)
        self._project_to_boardroom(workspace_id, record)
        return record, pointer

    @staticmethod
    def _normalise_assumptions(raw: dict[str, Any]) -> dict[str, Any]:
        months = int(_number(raw.get("forecast_months")) or 12)
        if not 1 <= months <= 36:
            raise ValueError("forecast_months_must_be_between_1_and_36")

        def percent(name: str, default: float = 0.0) -> float:
            value = _number(raw.get(name))
            value = default if value is None else value
            if not -100 <= value <= 1000:
                raise ValueError(f"{name}_outside_supported_range")
            return round(value, 4)

        stock_month = int(_number(raw.get("stock_purchase_month")) or 1)
        if not 1 <= stock_month <= months:
            raise ValueError("stock_purchase_month_outside_forecast_horizon")
        result = {
            "forecast_months": months,
            "annual_revenue_growth_percent": percent("annual_revenue_growth_percent"),
            "revenue_change_percent": percent("revenue_change_percent"),
            "price_change_percent": percent("price_change_percent"),
            "volume_change_percent": percent("volume_change_percent"),
            "direct_cost_change_percent": percent("direct_cost_change_percent"),
            "overhead_change_percent": percent("overhead_change_percent"),
            "monthly_hiring_cost": max(0.0, _number(raw.get("monthly_hiring_cost")) or 0.0),
            "one_off_stock_purchase": max(0.0, _number(raw.get("one_off_stock_purchase")) or 0.0),
            "stock_purchase_month": stock_month,
            "opening_cash": _number(raw.get("opening_cash")),
            "minimum_cash_reserve": max(0.0, _number(raw.get("minimum_cash_reserve")) or 0.0),
            "sensitivity_percent": abs(percent("sensitivity_percent", 10.0)),
        }
        return result

    @staticmethod
    def _monthly_baseline(management: dict[str, Any], assumptions: dict[str, Any]) -> dict[str, float]:
        rows = {item.get("key"): item.get("actual") for item in management.get("kpis") or []}
        period_months = _month_count(management.get("period") or {})
        required = ("revenue", "direct_costs", "overheads", "ending_cash")
        missing = [key for key in required if _number(rows.get(key)) is None]
        if missing:
            raise ValueError(f"scenario_baseline_missing:{','.join(missing)}")
        opening_cash = assumptions.get("opening_cash")
        if opening_cash is None:
            opening_cash = _number(rows.get("ending_cash"))
        return {
            "revenue": round(float(rows["revenue"]) / period_months, 4),
            "direct_costs": round(float(rows["direct_costs"]) / period_months, 4),
            "overheads": round(float(rows["overheads"]) / period_months, 4),
            "opening_cash": round(float(opening_cash), 4),
            "source_period_months": round(period_months, 4),
        }

    @staticmethod
    def _variant(baseline: dict[str, float], assumptions: dict[str, Any], sensitivity: float) -> dict[str, Any]:
        monthly_growth = (1 + assumptions["annual_revenue_growth_percent"] / 100) ** (1 / 12) - 1
        revenue_shift = (
            assumptions["revenue_change_percent"]
            + assumptions["price_change_percent"]
            + assumptions["volume_change_percent"]
            + sensitivity
        ) / 100
        direct_shift = assumptions["direct_cost_change_percent"] / 100
        volume_shift = (assumptions["volume_change_percent"] + sensitivity) / 100
        overhead_shift = assumptions["overhead_change_percent"] / 100
        cash = baseline["opening_cash"]
        rows: list[dict[str, Any]] = []
        for month in range(1, assumptions["forecast_months"] + 1):
            revenue = baseline["revenue"] * (1 + revenue_shift) * ((1 + monthly_growth) ** (month - 1))
            direct = baseline["direct_costs"] * (1 + direct_shift) * (1 + volume_shift)
            overheads = baseline["overheads"] * (1 + overhead_shift) + assumptions["monthly_hiring_cost"]
            stock = assumptions["one_off_stock_purchase"] if month == assumptions["stock_purchase_month"] else 0.0
            gross_profit = revenue - direct
            operating_profit = gross_profit - overheads
            movement = operating_profit - stock
            cash += movement
            rows.append({
                "month": month,
                "revenue": round(revenue, 2),
                "direct_costs": round(direct, 2),
                "gross_profit": round(gross_profit, 2),
                "overheads": round(overheads, 2),
                "operating_profit": round(operating_profit, 2),
                "stock_purchase": round(stock, 2),
                "net_cash_movement": round(movement, 2),
                "closing_cash": round(cash, 2),
            })
        reserve = assumptions["minimum_cash_reserve"]
        return {
            "months": rows,
            "summary": {
                "total_revenue": round(sum(item["revenue"] for item in rows), 2),
                "total_operating_profit": round(sum(item["operating_profit"] for item in rows), 2),
                "total_net_cash_movement": round(sum(item["net_cash_movement"] for item in rows), 2),
                "closing_cash": rows[-1]["closing_cash"],
                "minimum_cash": min(item["closing_cash"] for item in rows),
                "minimum_cash_reserve": reserve,
                "months_below_reserve": [item["month"] for item in rows if item["closing_cash"] < reserve],
            },
        }

    def _scenario_dir(self, workspace_id: str) -> Path:
        root = self.artifact_root or AIONBusinessPaths.business_container_dir(workspace_id)
        path = root / "finance" / "scenarios"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _store(self, workspace_id: str, record: dict[str, Any]) -> Path:
        path = self._scenario_dir(workspace_id) / f"{record['scenario_id']}.json"
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            self._verify(existing)
            if existing.get("scenario_hash") != record.get("scenario_hash"):
                raise ValueError(f"scenario_id_conflict:{record['scenario_id']}")
            return path
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)
        return path

    def _register_pointer(self, workspace_id: str, record: dict[str, Any], path: Path) -> dict[str, Any]:
        tree = WorkflowFileCabinetRepository.load(workspace_id)
        folders = tree.get("folders")
        if not isinstance(folders, list):
            folders = list((tree.get("root") or {}).get("children") or [])
            tree["folders"] = folders
        finance = _ensure_folder(folders, "folder_finance", "Finance", "department")
        scenarios = _ensure_folder(finance["children"], "folder_finance_scenarios", "Scenarios")
        storage_path = str(path)
        try:
            storage_path = str(path.relative_to(AIONBusinessPaths.ROOT))
        except ValueError:
            pass
        pointer = {
            "id": f"finance_scenario_pointer_{record['scenario_id']}",
            "name": record["name"],
            "type": "business_container_artifact",
            "document_type": "finance_scenario",
            "source_of_truth": "business_container",
            "file_cabinet_role": "index_pointer_only",
            "status": record["status"],
            "target": {
                "business_container_id": workspace_id,
                "sub_container": "finance",
                "category": "scenarios",
                "storage_path": storage_path,
                "scenario_id": record["scenario_id"],
                "scenario_hash": record["scenario_hash"],
            },
        }
        index = next((i for i, item in enumerate(scenarios["children"]) if item.get("id") == pointer["id"]), None)
        if index is None:
            scenarios["children"].append(pointer)
        else:
            scenarios["children"][index] = pointer
        tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}
        WorkflowFileCabinetRepository.save(workspace_id, tree)
        return pointer

    def _write_intelligence(self, workspace_id: str, record: dict[str, Any], path: Path) -> None:
        ledger = self.container_repository.load_optional_dict(workspace_id, "department_intelligence") or {
            "id": f"{workspace_id}.department_intelligence",
            "workspace_id": workspace_id,
            "kind": "department_intelligence",
            "meta": {"workspace_id": workspace_id, "container_key": "department_intelligence", "source": "aion_finance_pilot"},
            "departments": {},
            "revision": 1,
        }
        updated = deepcopy(ledger)
        finance = updated.setdefault("departments", {}).setdefault("finance", {"department": "finance"})
        summary = {
            "scenario_id": record["scenario_id"],
            "name": record["name"],
            "status": record["status"],
            "created_at": record["created_at"],
            "currency": record["currency"],
            "assumptions": record["assumptions"],
            "variant_summaries": {key: value["summary"] for key, value in record["variants"].items()},
            "scenario_hash": record["scenario_hash"],
            "storage_path": str(path),
        }
        finance.setdefault("scenarios", {})[record["scenario_id"]] = summary
        finance["latest_scenario"] = summary
        updated["revision"] = int(updated.get("revision") or 1) + 1
        updated.setdefault("meta", {})["updated_at"] = record["created_at"]
        self.container_repository.save_dict(workspace_id, "department_intelligence", updated)

    def _project_to_boardroom(self, workspace_id: str, record: dict[str, Any]) -> None:
        snapshot = self.container_repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if snapshot is None:
            return
        runtime = snapshot.setdefault("boardroom", {}).setdefault("runtime", {})
        summary = {
            "scenario_id": record["scenario_id"],
            "name": record["name"],
            "status": record["status"],
            "created_at": record["created_at"],
            "currency": record["currency"],
            "variant_summaries": {key: value["summary"] for key, value in record["variants"].items()},
            "scenario_hash": record["scenario_hash"],
        }
        runtime.setdefault("finance_scenarios", {})[record["scenario_id"]] = summary
        runtime["latest_finance_scenario"] = summary
        self.container_repository.save_dict(workspace_id, "boardroom_snapshot", snapshot)

    def list(self, workspace_id: str) -> list[dict[str, Any]]:
        path = self._scenario_dir(workspace_id)
        records = []
        for item in sorted(path.glob("*.json"), key=lambda candidate: candidate.stat().st_mtime, reverse=True):
            try:
                record = json.loads(item.read_text(encoding="utf-8"))
                self._verify(record)
                records.append(record)
            except (OSError, ValueError):
                raise ValueError(f"finance_scenario_integrity_failed:{item.name}")
        return records

    @staticmethod
    def _verify(record: dict[str, Any]) -> None:
        expected = str(record.get("scenario_hash") or "")
        payload = dict(record)
        payload.pop("scenario_hash", None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError(f"scenario_hash_mismatch:{record.get('scenario_id') or 'unknown'}")
