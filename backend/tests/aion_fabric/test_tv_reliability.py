from __future__ import annotations

from backend.modules.aion_fabric.tv_reliability import TelevisionReliabilityQualification


def test_contract_and_transport_cases_do_not_close_field_qualification(tmp_path):
    qualification = TelevisionReliabilityQualification(tmp_path)
    for area in qualification.REQUIRED_AREAS:
        qualification.record(
            device_id="tv_1", adapter="lg_webos_gateway", area=area,
            operation=area, outcome="verified", evidence_source="simulated_contract",
            evidence_id=f"sim-{area}",
        )
    report = qualification.report(device_id="tv_1", adapter="lg_webos_gateway", minimum_field_cases=1)
    assert report["field_cases"] == 0
    assert report["section_3_closed"] is False
    assert len(report["missing_areas"]) == len(qualification.REQUIRED_AREAS)


def test_all_areas_and_95_percent_field_success_close_section(tmp_path):
    qualification = TelevisionReliabilityQualification(tmp_path)
    areas = list(qualification.REQUIRED_AREAS)
    for index in range(20):
        qualification.record(
            device_id="tv_1", adapter="lg_webos_gateway", area=areas[index % len(areas)],
            operation=f"case-{index}", outcome="not_verified" if index == 19 else "verified",
            evidence_source="structured_screen_observation", evidence_id=f"field-{index}",
            recovered=index == 7,
        )
    report = qualification.report(device_id="tv_1", adapter="lg_webos_gateway")
    assert report["field_cases"] == 20
    assert report["success_or_recovery_rate"] == 0.95
    assert report["missing_areas"] == []
    assert report["section_3_closed"] is True


def test_navigation_records_are_idempotent_and_honest_about_transport(tmp_path):
    qualification = TelevisionReliabilityQualification(tmp_path)
    transaction = {
        "transaction_id": "nav_one", "device_id": "tv_1", "goal": "left",
        "status": "verified", "after_evidence": {"kind": "structured_observation"},
        "route_index": 1,
    }
    qualification.record_navigation(transaction)
    qualification.record_navigation(transaction)
    transport = {
        "transaction_id": "nav_two", "device_id": "tv_1", "goal": "right",
        "status": "not_verified", "after_evidence": {"kind": "transport_failure"},
    }
    qualification.record_navigation(transport)
    report = qualification.report(device_id="tv_1", minimum_field_cases=1)
    assert report["field_cases"] == 1
    assert report["verified_or_recovered"] == 1
    assert report["transport_only_excluded"] == 1


def test_owner_visual_confirmation_is_field_evidence(tmp_path):
    qualification = TelevisionReliabilityQualification(tmp_path)
    record = qualification.record_navigation({
        "transaction_id": "nav_owner", "device_id": "tv_1", "goal": "profile_2",
        "status": "verified", "route_index": 0,
        "after_evidence": {"kind": "owner_visual_confirmation", "confirmed": True},
    })
    assert record["area"] == "profile_selection"
    assert record["evidence_source"] == "owner_visual_confirmation"
