"""Read-only reconciliation of accepted spreadsheet facts with Xero evidence."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


ALIASES = {
    "revenue": {"revenue", "sales", "net sales", "turnover", "total income", "total revenue"},
    "direct_costs": {"direct costs", "cost of sales", "cogs", "total direct costs"},
    "gross_profit": {"gross profit"},
    "overheads": {"overheads", "operating expenses", "total operating expenses"},
    "operating_profit": {"operating profit", "ebitda", "net operating profit"},
    "net_profit": {"net profit", "profit after tax"},
    "ending_cash": {"ending cash", "closing cash", "cash balance", "bank balance"},
    "debtors": {"debtors", "accounts receivable", "trade debtors"},
    "creditors": {"creditors", "accounts payable", "trade creditors"},
}


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


def _number(value: Any) -> float | None:
    try:
        text = str(value).replace(",", "").replace("€", "").replace("£", "").strip()
        if text.startswith("(") and text.endswith(")"):
            text = f"-{text[1:-1]}"
        return float(text)
    except (TypeError, ValueError):
        return None


def _metric(label: Any) -> str | None:
    name = re.sub(r"\s+", " ", str(label or "").replace("_", " ").strip().lower())
    return next((key for key, aliases in ALIASES.items() if name in aliases), None)


def _period(value: Any) -> dict[str, str | None]:
    record = value if isinstance(value, dict) else {}
    return {"from": record.get("from") or record.get("start"), "to": record.get("to") or record.get("end")}


class FinanceReconciliationService:
    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()

    def run(self, workspace_id: str, *, artifact_periods: dict[str, Any] | None = None,
            tolerance: float = 0.01, created_at: str | None = None,
            created_by: str = "finance_pilot") -> dict[str, Any]:
        occurred_at = created_at or _now()
        model = self.repository.load_dict(workspace_id, "business_financial_model")
        xero, xero_period, xero_ref = self._xero_values(workspace_id, model)
        artifacts = self._artifact_values(model, artifact_periods or {})
        comparisons: list[dict[str, Any]] = []
        for artifact in artifacts:
            equivalent = artifact["period"] == xero_period and all(xero_period.values())
            for key in sorted(set(artifact["values"]) | set(xero)):
                spreadsheet = artifact["values"].get(key)
                provider = xero.get(key)
                difference = None if spreadsheet is None or provider is None else round(provider - spreadsheet, 4)
                allowed = max(abs(spreadsheet or 0) * tolerance, tolerance)
                status = (
                    "period_missing" if not all(artifact["period"].values())
                    else "period_mismatch" if not equivalent
                    else "missing_in_spreadsheet" if spreadsheet is None
                    else "missing_in_xero" if provider is None
                    else "match" if abs(difference or 0) <= allowed
                    else "conflict"
                )
                comparisons.append({
                    "artifact_id": artifact["artifact_id"], "metric": key,
                    "spreadsheet_value": spreadsheet, "xero_value": provider,
                    "difference": difference, "tolerance": allowed, "status": status,
                    "spreadsheet_period": artifact["period"], "xero_period": xero_period,
                })
        reconciliation_id = _safe(f"finance-reconciliation-{occurred_at}")
        counts = {status: sum(item["status"] == status for item in comparisons) for status in (
            "match", "conflict", "missing_in_spreadsheet", "missing_in_xero", "period_missing", "period_mismatch"
        )}
        record: dict[str, Any] = {
            "schema_version": "aion.finance_pilot.reconciliation.v1",
            "reconciliation_id": reconciliation_id, "workspace_id": workspace_id,
            "status": "review_required", "created_at": occurred_at, "created_by": created_by,
            "currency": model.get("currency") or "EUR", "tolerance_percent": tolerance * 100,
            "xero_evidence_ref": xero_ref, "artifact_count": len(artifacts),
            "comparison_count": len(comparisons), "counts": counts, "comparisons": comparisons,
            "review": None,
            "warnings": list(dict.fromkeys([
                *( ["No accepted spreadsheet artifacts are available."] if not artifacts else []),
                *( ["No comparable Xero report values were found in the latest read-only sync."] if not xero else []),
                *( ["A reporting period is required before spreadsheet values can be compared with Xero."] if counts["period_missing"] else []),
                *( ["Some spreadsheet and Xero reporting periods do not match."] if counts["period_mismatch"] else []),
            ])),
            "external_writes_performed": False, "canonical_values_changed": False,
            "source_financial_model_hash": canonical_contract_hash(model),
        }
        record["reconciliation_hash"] = canonical_contract_hash(record)
        path = self._store(workspace_id, record)
        self._index(workspace_id, record, path)
        self._project(workspace_id, record, path)
        return record

    def review(self, workspace_id: str, reconciliation_id: str, *, decision: str,
               reviewed_by: str, notes: str | None = None, reviewed_at: str | None = None) -> dict[str, Any]:
        if decision not in {"keep_spreadsheet", "prefer_xero", "no_change", "needs_investigation"}:
            raise ValueError("invalid_reconciliation_decision")
        path = self._dir(workspace_id) / f"{_safe(reconciliation_id)}.json"
        if not path.exists():
            raise FileNotFoundError(f"Finance reconciliation not found: {reconciliation_id}")
        record = json.loads(path.read_text(encoding="utf-8"))
        self._verify(record)
        record["review"] = {"decision": decision, "reviewed_by": reviewed_by, "reviewed_at": reviewed_at or _now(), "notes": notes}
        record["status"] = "reviewed_requires_separate_canonical_update" if decision in {"keep_spreadsheet", "prefer_xero"} else "reviewed"
        record["canonical_values_changed"] = False
        record.pop("reconciliation_hash", None)
        record["reconciliation_hash"] = canonical_contract_hash(record)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._project(workspace_id, record, path)
        return record

    def list(self, workspace_id: str) -> list[dict[str, Any]]:
        records = []
        for path in sorted(self._dir(workspace_id).glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            record = json.loads(path.read_text(encoding="utf-8")); self._verify(record); records.append(record)
        return records

    def _xero_values(self, workspace_id: str, model: dict[str, Any]) -> tuple[dict[str, float], dict[str, Any], dict[str, Any]]:
        xero = (model.get("integration_evidence") or {}).get("xero") or {}
        ref = xero.get("evidence_ref") or {}
        sync_id = ref.get("sync_id") or xero.get("sync_id")
        values: dict[str, float] = {}
        if sync_id:
            sync_dir = AIONBusinessPaths.business_container_dir(workspace_id) / "integrations/xero/syncs" / str(sync_id)
            for name in ("profit_and_loss.json", "balance_sheet.json", "bank_summary.json"):
                path = sync_dir / name
                if path.exists():
                    self._walk_xero(json.loads(path.read_text(encoding="utf-8")), values)
        return values, _period(xero.get("period") or ref.get("period")), ref

    def _walk_xero(self, value: Any, output: dict[str, float]) -> None:
        if isinstance(value, list):
            for item in value: self._walk_xero(item, output)
            return
        if not isinstance(value, dict): return
        cells = value.get("Cells")
        if isinstance(cells, list) and cells:
            labels = [item.get("Value") for item in cells if isinstance(item, dict)]
            key = _metric(labels[0] if labels else None)
            numbers = [_number(item) for item in labels[1:]]
            numbers = [item for item in numbers if item is not None]
            if key and numbers: output[key] = numbers[-1]
        for child in value.values():
            if isinstance(child, (dict, list)): self._walk_xero(child, output)

    def _artifact_values(self, model: dict[str, Any], overrides: dict[str, Any]) -> list[dict[str, Any]]:
        result = []
        for artifact_id, raw in ((model.get("external_data") or {}).get("artifacts") or {}).items():
            if str(raw.get("verification_status") or "") != "accepted_from_source_document": continue
            values: dict[str, float] = {}
            for fact in raw.get("facts") or []:
                key = _metric(fact.get("source_column") or str(fact.get("field") or "").split(".")[-1])
                number = _number(fact.get("value"))
                if key and number is not None: values[key] = number
            result.append({"artifact_id": artifact_id, "values": values, "period": _period(overrides.get(artifact_id) or overrides.get("*") or raw.get("period"))})
        return result

    def _dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/reconciliations"; path.mkdir(parents=True, exist_ok=True); return path

    def _store(self, workspace_id: str, record: dict[str, Any]) -> Path:
        path = self._dir(workspace_id) / f"{record['reconciliation_id']}.json"; path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path

    def _index(self, workspace_id: str, record: dict[str, Any], path: Path) -> None:
        tree = WorkflowFileCabinetRepository.load(workspace_id); folders = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        finance = next((item for item in folders if item.get("id") == "folder_finance"), None)
        if finance is None: finance = {"id": "folder_finance", "name": "Finance", "type": "department", "children": []}; folders.append(finance)
        children = finance.setdefault("children", []); reconciliations = next((item for item in children if item.get("id") == "folder_finance_reconciliations"), None)
        if reconciliations is None: reconciliations = {"id": "folder_finance_reconciliations", "name": "Reconciliations", "type": "folder", "children": []}; children.append(reconciliations)
        reconciliations["children"].append({"id": f"finance_reconciliation_pointer_{record['reconciliation_id']}", "name": record["reconciliation_id"], "type": "business_container_artifact", "document_type": "finance_reconciliation", "status": record["status"], "target": {"storage_path": str(path), "reconciliation_hash": record["reconciliation_hash"]}})
        tree["folders"] = folders; tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}; WorkflowFileCabinetRepository.save(workspace_id, tree)

    def _project(self, workspace_id: str, record: dict[str, Any], path: Path) -> None:
        ledger = self.repository.load_optional_dict(workspace_id, "department_intelligence") or {"id": f"{workspace_id}.department_intelligence", "workspace_id": workspace_id, "kind": "department_intelligence", "meta": {}, "departments": {}, "revision": 1}
        updated = deepcopy(ledger); finance = updated.setdefault("departments", {}).setdefault("finance", {"department": "finance"})
        summary = {key: record[key] for key in ("reconciliation_id", "status", "created_at", "counts", "warnings", "review", "reconciliation_hash")}; summary["storage_path"] = str(path)
        finance.setdefault("reconciliations", {})[record["reconciliation_id"]] = summary; finance["latest_reconciliation"] = summary; updated["revision"] = int(updated.get("revision") or 1) + 1; self.repository.save_dict(workspace_id, "department_intelligence", updated)
        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom is not None:
            runtime = boardroom.setdefault("boardroom", {}).setdefault("runtime", {}); runtime["latest_finance_reconciliation"] = summary; self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)

    @staticmethod
    def _verify(record: dict[str, Any]) -> None:
        expected = record.get("reconciliation_hash"); payload = dict(record); payload.pop("reconciliation_hash", None)
        if not expected or canonical_contract_hash(payload) != expected: raise ValueError("finance_reconciliation_hash_mismatch")
