from backend.services.aion_mission_mode.business_container_artifacts import (
    ALLOWED_BUSINESS_SUB_CONTAINERS,
    USER_USABLE_ARTIFACT_TYPES,
)
from backend.services.aion_mission_mode.department_artifact_persistence import (
    business_container_id_for_business,
    commit_department_artifact_from_pilot_result,
    summarize_department_artifact_records,
)


def make_pilot_result_and_tool_item(department_id="marketing"):
    tool_item = {
        "business_id": "home-fixed",
        "mission_id": "mission_23v",
        "mission_run_id": "run_001",
        "department_id": department_id,
        "department_display_name": department_id.title(),
        "task_id": f"{department_id}_task_001",
        "title": f"{department_id} task",
        "department_capability": "campaign.plan" if department_id == "marketing" else "document.create",
        "gateway_tool_name": "generate_copy",
        "local_tool_id": "tool.internal.generate_copy.v1",
        "artifact_type": "markdown",
        "tool_execution_item_hash": f"sha256:{department_id}toolhash",
    }

    pilot_result = {
        "business_id": "home-fixed",
        "mission_id": "mission_23v",
        "mission_run_id": "run_001",
        "step_id": f"{department_id}_task_001",
        "department_id": department_id,
        "department_capability": tool_item["department_capability"],
        "output_text": "Draft output",
        "artifact_hash": f"sha256:{department_id}artifacthash",
        "receipt_hash": f"sha256:{department_id}receipthash",
        "execution_hash": f"sha256:{department_id}executionhash",
        "artifact_card": {
            "artifact_name": f"{department_id}_draft.md",
            "artifact_hash": f"sha256:{department_id}artifacthash",
            "artifact_receipt_hash": f"sha256:{department_id}receipthash",
            "business_container_relative_path": f"business/home-fixed/missions/mission_23v/runs/run_001/artifacts/{department_id}_draft.md",
        },
    }
    return pilot_result, tool_item


def test_phase23v_department_sub_containers_are_allowed():
    for department in ["marketing", "pilot", "sales", "finance", "operations", "support", "builder"]:
        assert department in ALLOWED_BUSINESS_SUB_CONTAINERS

    assert "markdown" in USER_USABLE_ARTIFACT_TYPES
    assert "text" in USER_USABLE_ARTIFACT_TYPES
    assert "json" in USER_USABLE_ARTIFACT_TYPES


def test_phase23v_business_container_id_rejects_global_targets():
    assert business_container_id_for_business("home-fixed") == "home-fixed"

    for invalid in ["global", "root", "session_vfs", "tmp", "temp"]:
        try:
            business_container_id_for_business(invalid)
            raised = False
        except ValueError:
            raised = True
        assert raised is True


def test_phase23v_marketing_artifact_binds_to_business_department_container():
    pilot_result, tool_item = make_pilot_result_and_tool_item("marketing")

    record = commit_department_artifact_from_pilot_result(
        pilot_result=pilot_result,
        tool_execution_item=tool_item,
    )

    assert record["department_id"] == "marketing"
    assert record["target"]["business_id"] == "home-fixed"
    assert record["target"]["business_container_id"] == "home-fixed"
    assert record["target"]["sub_container"] == "marketing"
    assert record["storage_path"].startswith("business_containers/home-fixed/marketing/")
    assert record["record_valid"] is True
    assert record["merkle_triad_valid"] is True
    assert record["department_artifact_state"] == "department_container_bound"


def test_phase23v_builder_artifact_binds_to_builder_container():
    pilot_result, tool_item = make_pilot_result_and_tool_item("builder")

    record = commit_department_artifact_from_pilot_result(
        pilot_result=pilot_result,
        tool_execution_item=tool_item,
    )

    assert record["department_id"] == "builder"
    assert record["target"]["sub_container"] == "builder"
    assert record["storage_path"].startswith("business_containers/home-fixed/builder/")


def test_phase23v_replay_locator_contains_required_trace_fields():
    pilot_result, tool_item = make_pilot_result_and_tool_item("operations")

    record = commit_department_artifact_from_pilot_result(
        pilot_result=pilot_result,
        tool_execution_item=tool_item,
    )

    locator = record["replay_locator"]

    assert locator["business_id"] == "home-fixed"
    assert locator["business_container_id"] == "home-fixed"
    assert locator["department_id"] == "operations"
    assert locator["mission_id"] == "mission_23v"
    assert locator["mission_run_id"] == "run_001"
    assert locator["storage_path"] == record["storage_path"]
    assert record["replay_locator_hash"].startswith("sha256:")


def test_phase23v_summary_indexes_department_records():
    records = []
    for department in ["marketing", "finance", "sales"]:
        pilot_result, tool_item = make_pilot_result_and_tool_item(department)
        records.append(
            commit_department_artifact_from_pilot_result(
                pilot_result=pilot_result,
                tool_execution_item=tool_item,
            )
        )

    summary = summarize_department_artifact_records(records)

    assert summary["record_count"] == 3
    assert summary["department_ids"] == ["finance", "marketing", "sales"]
    assert summary["all_records_valid"] is True
    assert summary["all_merkle_triads_valid"] is True
    assert summary["live_external_side_effects_enabled"] is False
    assert summary["summary_hash"].startswith("sha256:")


def test_phase23v_rejects_unknown_department_target():
    pilot_result, tool_item = make_pilot_result_and_tool_item("unknown")

    try:
        commit_department_artifact_from_pilot_result(
            pilot_result=pilot_result,
            tool_execution_item=tool_item,
        )
        raised = False
    except ValueError as exc:
        raised = "unsupported_department_id" in str(exc)

    assert raised is True
