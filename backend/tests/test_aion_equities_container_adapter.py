from __future__ import annotations

from backend.modules.aion_equities.aion_equities_container_adapter import (
    AIONEquitiesContainerAdapter,
)


class _StubRuntime:
    def __init__(self):
        self.saved = {}

    def save_container(self, container_id, container):
        self.saved[container_id] = container
        return container


def test_company_container_builds_and_saves_company_doc():
    runtime = _StubRuntime()
    adapter = AIONEquitiesContainerAdapter(runtime=runtime)

    company = {
        "company_id": "company/ULVR.L",
        "ticker": "ULVR.L",
        "name": "Unilever PLC",
    }

    container = adapter.company_container(company)

    assert container["id"] == "equities/company/ULVR.L"
    assert container["kind"] == "equities_company"
    assert container["payload"]["company_id"] == "company/ULVR.L"
    assert "equities/company/ULVR.L" in runtime.saved


def test_assessment_container_builds_and_saves_doc():
    runtime = _StubRuntime()
    adapter = AIONEquitiesContainerAdapter(runtime=runtime)

    assessment = {
        "assessment_id": "assessment/company/ULVR.L/2026-03-01",
        "entity_id": "company/ULVR.L",
    }

    container = adapter.assessment_container(assessment)

    assert container["kind"] == "equities_assessment"
    assert container["meta"]["source_ref"] == assessment["assessment_id"]
    assert container["payload"]["entity_id"] == "company/ULVR.L"


def test_thesis_container_builds_and_saves_doc():
    runtime = _StubRuntime()
    adapter = AIONEquitiesContainerAdapter(runtime=runtime)

    thesis = {
        "thesis_id": "thesis/ULVR.L/long/bootstrap",
        "ticker": "ULVR.L",
    }

    container = adapter.thesis_container(thesis)

    assert container["kind"] == "equities_thesis"
    assert container["payload"]["thesis_id"] == thesis["thesis_id"]
    assert container["id"].startswith("equities/thesis/")


def test_trigger_map_and_pre_earnings_container_build_and_save_docs():
    runtime = _StubRuntime()
    adapter = AIONEquitiesContainerAdapter(runtime=runtime)

    trigger_map = {
        "company_trigger_map_id": "company/ULVR.L/trigger_map/2026Q1",
        "company_ref": "company/ULVR.L",
    }
    estimate = {
        "pre_earnings_estimate_id": "company/ULVR.L/pre_earnings/2026Q1",
        "company_ref": "company/ULVR.L",
    }

    trigger_container = adapter.trigger_map_container(trigger_map)
    estimate_container = adapter.pre_earnings_estimate_container(estimate)

    assert trigger_container["kind"] == "equities_trigger_map"
    assert estimate_container["kind"] == "equities_pre_earnings_estimate"
    assert trigger_container["meta"]["source_ref"] == trigger_map["company_trigger_map_id"]
    assert estimate_container["meta"]["source_ref"] == estimate["pre_earnings_estimate_id"]