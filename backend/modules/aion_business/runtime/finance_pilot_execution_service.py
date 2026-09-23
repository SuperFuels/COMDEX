"""Read-only Finance Pilot execution and Boardroom handback vertical."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import (
    DepartmentPilotWorkEnvelope,
    canonical_contract_hash,
)
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.department_context_assembler import (
    DepartmentContextAssembler,
)
from backend.modules.aion_business.runtime.department_pilot_contracts import (
    create_boardroom_handback,
    create_department_artifact,
    create_execution_receipt,
    create_intelligence_patch,
    create_provenance,
)
from backend.modules.aion_business.runtime.department_pilot_profiles import (
    get_department_pilot_profile,
)
from backend.modules.aion_business.runtime.department_pilot_repository import (
    DepartmentPilotRepository,
)
from backend.modules.aion_business.runtime.department_pilot_runtime import (
    DepartmentPilotRuntime,
)
from backend.modules.aion_business.runtime.finance_management_report_builder import (
    build_finance_management_report,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


def _metric_value(metrics: dict[str, Any], *names: str) -> float | None:
    for name in names:
        value = metrics.get(name)
        if isinstance(value, dict):
            value = value.get("value", value.get("amount"))
        try:
            if value is not None and str(value).strip() != "":
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _money(value: float | None, currency: str) -> str:
    return "not available" if value is None else f"{currency} {value:,.2f}"


def _percent(value: float | None) -> str:
    return "not available" if value is None else f"{value:,.1f}%"


def _ensure_folder(
    children: list[dict[str, Any]], node_id: str, name: str, node_type: str = "folder"
) -> dict[str, Any]:
    node = next((item for item in children if item.get("id") == node_id), None)
    if node is None:
        node = {"id": node_id, "name": name, "type": node_type, "children": []}
        children.append(node)
    node["name"] = name
    node["type"] = node_type
    node.setdefault("children", [])
    return node


class FinancePilotExecutionService:
    """Complete one approved Finance task without performing external writes."""

    def __init__(
        self,
        task_repository: DepartmentPilotRepository | None = None,
        container_repository: BusinessContainerRepository | None = None,
        *,
        artifact_root: Path | None = None,
    ) -> None:
        self.task_repository = task_repository or DepartmentPilotRepository()
        self.container_repository = container_repository or BusinessContainerRepository()
        self.runtime = DepartmentPilotRuntime(self.task_repository)
        self.context_assembler = DepartmentContextAssembler(self.container_repository)
        self.artifact_root = artifact_root

    def execute(
        self,
        workspace_id: str,
        task_id: str,
        *,
        actor_id: str = "finance_pilot",
        executed_at: str | None = None,
    ) -> tuple[DepartmentPilotWorkEnvelope, dict[str, Any], dict[str, Any]]:
        occurred_at = executed_at or _now()
        envelope = self.task_repository.load(workspace_id, "finance", task_id)
        if envelope.task.status == "completed":
            return envelope, self._load_report(envelope), {}
        self._assert_permission(envelope)

        if envelope.task.status == "queued":
            envelope = self.runtime.transition(
                workspace_id=workspace_id,
                department_id="finance",
                task_id=task_id,
                to_status="claimed",
                occurred_at=occurred_at,
                actor_id=actor_id,
                event_id=f"{task_id}-claimed",
                message="Finance Pilot claimed the approved Boardroom task.",
                progress_percent=10,
            )
        if envelope.task.status == "claimed":
            envelope = self.runtime.transition(
                workspace_id=workspace_id,
                department_id="finance",
                task_id=task_id,
                to_status="running",
                occurred_at=occurred_at,
                actor_id=actor_id,
                event_id=f"{task_id}-started",
                message="Finance Pilot started read-only analysis.",
                progress_percent=20,
            )
        if envelope.task.status != "running":
            raise ValueError(f"finance_task_not_executable_from_status:{envelope.task.status}")

        if not envelope.retrieved_evidence and envelope.task.context_refs:
            evidence = self.context_assembler.retrieve_for_task(
                envelope.task,
                retrieved_at=occurred_at,
                retrieved_by=actor_id,
            )
            envelope = self.runtime.attach_retrieved_evidence(
                workspace_id=workspace_id,
                department_id="finance",
                task_id=task_id,
                evidence=evidence,
            )

        report = self._build_report(envelope, occurred_at)
        artifact, pointer = self._store_report(envelope, report, occurred_at, actor_id)
        original_ledger, updated_ledger, patch = self._prepare_intelligence_writeback(
            envelope, report, artifact.artifact_id, occurred_at, actor_id
        )
        receipt = create_execution_receipt(
            receipt_id=f"receipt-{task_id}",
            task_id=task_id,
            department_id="finance",
            outcome=report["outcome"],
            started_at=envelope.task.started_at,
            completed_at=occurred_at,
            requested_payload_hash=envelope.package.package_hash,
            executed_payload_hash=artifact.content_hash,
            before_state_hash=envelope.envelope_hash,
            after_state_hash=canonical_contract_hash(updated_ledger),
            artifact_ids=[artifact.artifact_id],
            evidence_hashes=[item.retrieval_hash for item in envelope.retrieved_evidence],
            approval_ids=[],
            error_code=None,
            error_message=None,
            rollback_available=False,
            rollback_instructions=None,
            legacy_receipt_hash=None,
        )
        handback = create_boardroom_handback(
            handback_id=f"handback-{task_id}",
            package_id=envelope.package.package_id,
            task_id=task_id,
            department_id="finance",
            status="ready_for_boardroom",
            outcome=report["outcome"],
            executive_summary=report["executive_summary"],
            completed_actions=[envelope.task.title],
            unresolved_items=report["unresolved_items"],
            decisions_requested=report["decisions_requested"],
            metric_changes={
                "management_report": {
                    "schema_version": report["management_accounts"]["schema_version"],
                    "period": report["management_accounts"]["period"],
                    "currency": report["management_accounts"]["currency"],
                    "headline": report["management_accounts"]["headline"],
                    "kpis": report["management_accounts"]["kpis"],
                    "comparison_coverage": report["management_accounts"]["comparison_coverage"],
                    "evidence_freshness": report["management_accounts"]["evidence_freshness"],
                    "warnings": report["management_accounts"]["warnings"][:8],
                }
            },
            artifact_ids=[artifact.artifact_id],
            receipt_ids=[receipt.receipt_id],
            intelligence_patch_ids=[patch.patch_id],
            evidence_refs=[item.reference_id for item in envelope.retrieved_evidence],
            created_at=occurred_at,
            created_by=actor_id,
        )

        self.container_repository.save_dict(
            workspace_id, "department_intelligence", updated_ledger
        )
        try:
            completed = self.runtime.complete(
                workspace_id=workspace_id,
                department_id="finance",
                task_id=task_id,
                completed_at=occurred_at,
                actor_id=actor_id,
                event_id=f"{task_id}-completed",
                receipt=receipt,
                handback=handback,
                artifacts=[artifact],
                intelligence_patches=[patch],
            )
        except Exception:
            self.container_repository.save_dict(
                workspace_id, "department_intelligence", original_ledger
            )
            raise

        self._project_handback_to_boardroom(workspace_id, completed)
        return completed, report, pointer

    @staticmethod
    def _assert_permission(envelope: DepartmentPilotWorkEnvelope) -> None:
        profile = get_department_pilot_profile("finance") or {}
        allowed = set(profile.get("allowed_capabilities") or [])
        if envelope.task.department_id != "finance":
            raise ValueError("finance_executor_requires_finance_task")
        if envelope.task.capability not in allowed:
            raise PermissionError(
                f"finance_capability_not_permitted:{envelope.task.capability}"
            )
        if profile.get("tool_permissions", {}).get("approved_live_external"):
            raise ValueError("finance_read_only_profile_must_not_enable_live_external_tools")

    def _context_by_kind(self, envelope: DepartmentPilotWorkEnvelope) -> dict[str, Any]:
        reference_by_id = {item.reference_id: item for item in envelope.task.context_refs}
        context: dict[str, Any] = {}
        for evidence in envelope.retrieved_evidence:
            reference = reference_by_id.get(evidence.reference_id)
            if reference and evidence.retrieval_status == "retrieved":
                context[reference.container_kind] = evidence.data
        return context

    def _build_report(
        self, envelope: DepartmentPilotWorkEnvelope, generated_at: str
    ) -> dict[str, Any]:
        context = self._context_by_kind(envelope)
        financial = context.get("business_financial_model") or {}
        operating = context.get("business_operating_model") or {}
        identity = context.get("business_identity") or {}
        metrics = financial.get("metrics") or {}
        currency = str(
            financial.get("currency") or operating.get("currency") or identity.get("currency") or "EUR"
        )
        revenue = _metric_value(metrics, "revenue", "net_sales", "sales")
        gross_profit = _metric_value(metrics, "gross_profit")
        operating_profit = _metric_value(metrics, "operating_profit", "ebitda_profit")
        cash = _metric_value(metrics, "ending_cash", "cash", "cash_balance")
        issues = [
            f"{item.reference_id}: {item.issue}"
            for item in envelope.retrieved_evidence
            if item.retrieval_status != "retrieved"
        ]
        missing = list(financial.get("missing_information") or [])
        management = build_finance_management_report(
            financial,
            generated_at=generated_at,
            retrieval_issues=issues,
        )
        headline = management["headline"]
        revenue = headline.get("revenue") if headline.get("revenue") is not None else revenue
        gross_profit = headline.get("gross_profit") if headline.get("gross_profit") is not None else gross_profit
        operating_profit = (
            headline.get("operating_profit")
            if headline.get("operating_profit") is not None
            else operating_profit
        )
        cash = headline.get("ending_cash") if headline.get("ending_cash") is not None else cash
        gross_margin = next(
            (item.get("actual") for item in management["kpis"] if item.get("key") == "gross_margin_percent"),
            None,
        )
        unresolved = list(dict.fromkeys([
            *issues,
            *[str(item) for item in missing],
            *management["warnings"],
        ]))[:30]
        available = sum(value is not None for value in (revenue, gross_profit, operating_profit, cash))
        outcome = "succeeded" if not issues and available else "partial"
        executive_summary = (
            f"Finance completed the approved read-only Boardroom analysis. "
            f"Revenue: {_money(revenue, currency)}; gross profit: {_money(gross_profit, currency)}; "
            f"gross margin: {_percent(gross_margin)}; operating profit: {_money(operating_profit, currency)}; "
            f"closing cash: {_money(cash, currency)}. "
            f"Reporting period: {management['period']['label']}."
        )
        return {
            "schema_version": "aion.finance_pilot.management_report.v2",
            "report_id": f"finance-report-{envelope.task.task_id}",
            "workspace_id": envelope.task.workspace_id,
            "task_id": envelope.task.task_id,
            "package_id": envelope.package.package_id,
            "generated_at": generated_at,
            "generated_by": "finance_pilot",
            "mode": "read_only",
            "outcome": outcome,
            "title": envelope.task.title,
            "objective": envelope.task.objective,
            "executive_summary": executive_summary,
            "metrics": {
                "currency": currency,
                "revenue": revenue,
                "gross_profit": gross_profit,
                "operating_profit": operating_profit,
                "ending_cash": cash,
            },
            "management_accounts": management,
            "operating_context": operating,
            "unresolved_items": unresolved,
            "decisions_requested": (
                ["Confirm or supply the missing Finance information before relying on the affected figures."]
                if unresolved
                else []
            ),
            "evidence": [
                {
                    "reference_id": item.reference_id,
                    "retrieval_status": item.retrieval_status,
                    "verification_state": item.verification_state,
                    "retrieval_hash": item.retrieval_hash,
                }
                for item in envelope.retrieved_evidence
            ],
            "external_writes_performed": False,
        }

    def _report_dir(self, workspace_id: str) -> Path:
        root = self.artifact_root or AIONBusinessPaths.business_container_dir(workspace_id)
        path = root / "finance" / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _store_report(
        self,
        envelope: DepartmentPilotWorkEnvelope,
        report: dict[str, Any],
        created_at: str,
        created_by: str,
    ) -> tuple[Any, dict[str, Any]]:
        artifact_id = _safe_id(report["report_id"])
        destination = self._report_dir(envelope.task.workspace_id) / f"{artifact_id}.json"
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(destination)
        content_hash = canonical_contract_hash(report)
        relative_path = str(destination)
        try:
            relative_path = str(destination.relative_to(AIONBusinessPaths.ROOT))
        except ValueError:
            pass
        file_cabinet_path = f"Finance/Reports/{destination.name}"
        provenance = create_provenance(
            created_by=created_by,
            created_at=created_at,
            source_system="aion_finance_pilot",
            source_record_id=envelope.task.task_id,
            source_hash=envelope.envelope_hash,
            correlation_id=envelope.package.boardroom_session_id,
        )
        artifact = create_department_artifact(
            artifact_id=artifact_id,
            task_id=envelope.task.task_id,
            department_id="finance",
            artifact_type="finance_boardroom_report",
            title=f"Finance Boardroom report · {envelope.task.title}",
            status="accepted",
            business_container_path=relative_path,
            file_cabinet_path=file_cabinet_path,
            media_type="application/json",
            content_hash=content_hash,
            evidence_refs=[item.reference_id for item in envelope.retrieved_evidence],
            created_at=created_at,
            created_by=created_by,
            provenance=provenance,
        )
        pointer = self._register_file_cabinet_pointer(envelope, artifact)
        return artifact, pointer

    @staticmethod
    def _register_file_cabinet_pointer(
        envelope: DepartmentPilotWorkEnvelope, artifact: Any
    ) -> dict[str, Any]:
        tree = WorkflowFileCabinetRepository.load(envelope.task.workspace_id)
        folders = tree.get("folders")
        if not isinstance(folders, list):
            folders = list((tree.get("root") or {}).get("children") or [])
            tree["folders"] = folders
        finance = _ensure_folder(folders, "folder_finance", "Finance", "department")
        reports = _ensure_folder(
            finance["children"], "folder_finance_reports", "Reports"
        )
        pointer = {
            "id": f"department_pilot_artifact_pointer_{artifact.artifact_id}",
            "name": artifact.title,
            "type": "business_container_artifact",
            "document_type": artifact.artifact_type,
            "source_of_truth": "business_container",
            "file_cabinet_role": "index_pointer_only",
            "status": artifact.status,
            "target": {
                "business_container_id": envelope.task.workspace_id,
                "sub_container": "finance",
                "category": "reports",
                "storage_path": artifact.business_container_path,
                "artifact_id": artifact.artifact_id,
                "artifact_hash": artifact.content_hash,
                "task_id": envelope.task.task_id,
                "package_id": envelope.package.package_id,
            },
        }
        existing = next(
            (index for index, item in enumerate(reports["children"]) if item.get("id") == pointer["id"]),
            None,
        )
        if existing is None:
            reports["children"].append(pointer)
        else:
            reports["children"][existing] = pointer
        tree["root"] = {
            **(tree.get("root") or {}),
            "id": "root",
            "type": "folder",
            "name": "Workflows",
            "children": folders,
        }
        WorkflowFileCabinetRepository.save(envelope.task.workspace_id, tree)
        return pointer

    def _prepare_intelligence_writeback(
        self,
        envelope: DepartmentPilotWorkEnvelope,
        report: dict[str, Any],
        artifact_id: str,
        created_at: str,
        created_by: str,
    ) -> tuple[dict[str, Any], dict[str, Any], Any]:
        original = self.container_repository.load_optional_dict(
            envelope.task.workspace_id, "department_intelligence"
        ) or {
            "id": f"{envelope.task.workspace_id}.department_intelligence",
            "workspace_id": envelope.task.workspace_id,
            "kind": "department_intelligence",
            "meta": {
                "workspace_id": envelope.task.workspace_id,
                "container_key": "department_intelligence",
                "source": "aion_finance_pilot",
            },
            "departments": {},
            "revision": 1,
        }
        updated = deepcopy(original)
        base_revision = int(original.get("revision") or 1)
        departments = updated.setdefault("departments", {})
        finance = departments.setdefault("finance", {"department": "finance"})
        results = finance.setdefault("pilot_results", {})
        result_record = {
            "task_id": envelope.task.task_id,
            "package_id": envelope.package.package_id,
            "status": "ready_for_boardroom",
            "outcome": report["outcome"],
            "executive_summary": report["executive_summary"],
            "metrics": report["metrics"],
            "management_report": {
                "schema_version": report["management_accounts"]["schema_version"],
                "period": report["management_accounts"]["period"],
                "headline": report["management_accounts"]["headline"],
                "kpis": report["management_accounts"]["kpis"],
                "comparison_coverage": report["management_accounts"]["comparison_coverage"],
                "evidence_freshness": report["management_accounts"]["evidence_freshness"],
                "warnings": report["management_accounts"]["warnings"],
            },
            "artifact_id": artifact_id,
            "evidence_refs": [item.reference_id for item in envelope.retrieved_evidence],
            "updated_at": created_at,
        }
        results[envelope.task.task_id] = result_record
        finance["latest_pilot_result"] = result_record
        finance["status"] = "pilot_result_ready_for_boardroom"
        updated["revision"] = base_revision + 1
        updated.setdefault("meta", {})["source"] = "aion_finance_pilot"
        updated["meta"]["updated_at"] = created_at
        verification = (
            "source_backed"
            if envelope.retrieved_evidence
            and all(item.retrieval_status == "retrieved" for item in envelope.retrieved_evidence)
            else "unverified"
        )
        patch = create_intelligence_patch(
            patch_id=f"patch-{envelope.task.task_id}",
            task_id=envelope.task.task_id,
            department_id="finance",
            base_revision=base_revision,
            operations=[
                {
                    "op": "add",
                    "path": f"/departments/finance/pilot_results/{envelope.task.task_id}",
                    "value": result_record,
                },
                {
                    "op": "replace",
                    "path": "/departments/finance/latest_pilot_result",
                    "value": result_record,
                },
            ],
            evidence_refs=[item.reference_id for item in envelope.retrieved_evidence],
            verification_state=verification,
            created_at=created_at,
            created_by=created_by,
        )
        return original, updated, patch

    def _project_handback_to_boardroom(
        self, workspace_id: str, envelope: DepartmentPilotWorkEnvelope
    ) -> None:
        snapshot = self.container_repository.load_optional_dict(
            workspace_id, "boardroom_snapshot"
        )
        if snapshot is None or envelope.handback is None:
            return
        boardroom = snapshot.setdefault("boardroom", {})
        runtime = boardroom.setdefault("runtime", {})
        handbacks = runtime.setdefault("department_pilot_handbacks", {})
        handbacks[envelope.task.task_id] = envelope.handback.model_dump(mode="json")
        runtime["latest_department_pilot_handback"] = envelope.handback.model_dump(
            mode="json"
        )
        self.container_repository.save_dict(workspace_id, "boardroom_snapshot", snapshot)

    @staticmethod
    def _load_report(envelope: DepartmentPilotWorkEnvelope) -> dict[str, Any]:
        if not envelope.artifacts:
            return {}
        path = Path(envelope.artifacts[-1].business_container_path)
        if not path.is_absolute():
            path = AIONBusinessPaths.ROOT / path
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
