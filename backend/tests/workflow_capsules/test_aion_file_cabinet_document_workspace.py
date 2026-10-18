from __future__ import annotations

import json

from openpyxl import Workbook

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)


def test_spreadsheet_preview_and_governed_protection(tmp_path, monkeypatch):
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", tmp_path / "AION_BUSINESS")
    workspace = "cabinet-test"
    artifact_dir = AIONBusinessPaths.ROOT / "business_containers" / workspace / "finance" / "spreadsheets"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = artifact_dir / "management.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Profit and loss"
    sheet.append(["Account", "Amount"])
    sheet.append(["Revenue", 1000])
    workbook.save(workbook_path)

    tree = WorkflowFileCabinetRepository.default_tree(workspace)
    tree["folders"] = [
        {
            "id": "finance",
            "name": "Finance",
            "type": "department",
            "children": [
                {
                    "id": "accepted-management-accounts",
                    "name": "Management accounts.xlsx",
                    "type": "business_container_artifact",
                    "document_type": "spreadsheet",
                    "source_of_truth": "business_container",
                    "status": "accepted",
                    "target": {
                        "storage_path": str(workbook_path.relative_to(AIONBusinessPaths.ROOT))
                    },
                }
            ],
        }
    ]
    WorkflowFileCabinetRepository.save(workspace, tree)

    preview = WorkflowFileCabinetRepository.preview(workspace, "accepted-management-accounts")
    assert preview["kind"] == "spreadsheet"
    assert preview["sheets"][0]["name"] == "Profit and loss"
    assert preview["sheets"][0]["rows"][1] == ["Revenue", "1000"]
    assert preview["protection"]["protected"] is True
    assert preview["protection"]["deletion_policy"] == "protected_record"


def test_user_owned_unaccepted_file_is_removable():
    protection = WorkflowFileCabinetRepository.protection(
        {
            "id": "user-note",
            "type": "business_container_artifact",
            "document_type": "document",
            "status": "uploaded",
            "provenance": {"created_by": "user_upload"},
            "deletion_policy": "user_removable",
        }
    )
    assert protection == {
        "protected": False,
        "deletion_policy": "user_removable",
        "reason": "User-owned item; removable with confirmation",
    }


def test_frontend_routes_artifacts_to_reader_and_workflows_to_canvas():
    source = (AIONBusinessPaths.ROOT.parent.parent / "desktop" / "mac" / "src" / "app.js")
    if not source.exists():
        source = __import__("pathlib").Path("desktop/mac/src/app.js")
    text = source.read_text(encoding="utf-8")
    assert "data-aion-file-cabinet-open-artifact" in text
    assert "aion-document-workspace-v1" in text
    assert 'state.activeTab = "operations_flow"' in text
    assert "isAionFileCabinetNodeProtected(found.node)" in text
    assert "Protected Board / evidence record" in text


def test_boardroom_json_preview_is_rendered_as_readable_minutes(tmp_path, monkeypatch):
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", tmp_path / "AION_BUSINESS")
    workspace = "home-fixed"
    artifact_path = AIONBusinessPaths.ROOT / "business_containers" / workspace / "pilot" / "meeting.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(
            {
                "session_id": "boardroom_session_1",
                "session_type": "business_assessment",
                "generated_at": "2026-08-23T18:13:27+00:00",
                "council_members": ["OpenAI", "Gemini / Google"],
                "business_context_packet": {"lines": ["Business name: Home Fixed"]},
                "boardroom_council_result": {
                    "consensus": {
                        "summary": "Review cash and capacity before launch.",
                        "risks": ["Capacity is not verified."],
                    }
                },
                "execution_boundary": {"approval_gated": True},
                "boardroom_session_packet_hash": "sha256:test",
            }
        ),
        encoding="utf-8",
    )
    tree = WorkflowFileCabinetRepository.default_tree(workspace)
    tree["folders"] = [
        {
            "id": "meeting-1",
            "name": "Boardroom Session",
            "type": "business_container_artifact",
            "document_type": "boardroom_session",
            "source_of_truth": "business_container",
            "target": {"storage_path": str(artifact_path.relative_to(AIONBusinessPaths.ROOT))},
        }
    ]
    WorkflowFileCabinetRepository.save(workspace, tree)

    preview = WorkflowFileCabinetRepository.preview(workspace, "meeting-1")
    text = "\n".join(block.get("text", "") for block in preview["blocks"])
    assert preview["kind"] == "document"
    assert "Board meeting minutes" in text
    assert "Review cash and capacity before launch." in text
    assert "Capacity is not verified." in text


def test_frontend_repairs_missing_legacy_boardroom_artifact_once():
    source = __import__("pathlib").Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
    assert "artifact_file_missing" in source
    assert "__aionPersistBoardroomSessionForItemV1" in source
    assert "Recovering and securely filing these meeting minutes" in source
