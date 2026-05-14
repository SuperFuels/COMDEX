from __future__ import annotations

from backend.modules.aion_equities.aion_equities_kg_bridge import AIONEquitiesKGBridge


class _StubKGWriter:
    def __init__(self):
        self.nodes = []
        self.edges = []

    def inject_node(self, *, container_id, node):
        self.nodes.append({"container_id": container_id, "node": node})
        return {"status": "ok"}

    def add_edge(self, src, dst, relation):
        self.edges.append({"src": src, "dst": dst, "relation": relation})
        return {"status": "ok"}


def test_write_company_injects_company_node():
    writer = _StubKGWriter()
    bridge = AIONEquitiesKGBridge(writer=writer)

    company = {
        "company_id": "company/ULVR.L",
        "ticker": "ULVR.L",
        "name": "Unilever PLC",
    }

    node = bridge.write_company(company)

    assert node["id"] == "company/ULVR.L"
    assert node["domain"] == "equities_company"
    assert len(writer.nodes) == 1
    assert writer.nodes[0]["container_id"] == "company/ULVR.L"


def test_write_assessment_injects_node_and_edge():
    writer = _StubKGWriter()
    bridge = AIONEquitiesKGBridge(writer=writer)

    assessment = {
        "assessment_id": "assessment/company/ULVR.L/2026-03-01",
        "entity_id": "company/ULVR.L",
        "entity_type": "company",
    }

    node = bridge.write_assessment(assessment)

    assert node["id"] == assessment["assessment_id"]
    assert len(writer.nodes) == 1
    assert len(writer.edges) == 1
    assert writer.edges[0] == {
        "src": "company/ULVR.L",
        "dst": assessment["assessment_id"],
        "relation": "evidence_source",
    }


def test_write_thesis_injects_node_and_supporting_edges():
    writer = _StubKGWriter()
    bridge = AIONEquitiesKGBridge(writer=writer)

    thesis = {
        "thesis_id": "thesis/ULVR.L/long/bootstrap",
        "ticker": "ULVR.L",
        "company_ref": "company/ULVR.L",
        "assessment_refs": [
            "assessment/company/ULVR.L/2026-03-01",
            "assessment/company/ULVR.L/2026-04-01",
        ],
    }

    node = bridge.write_thesis(thesis)

    assert node["id"] == thesis["thesis_id"]
    assert len(writer.nodes) == 1
    assert len(writer.edges) == 3
    assert writer.edges[0] == {
        "src": "company/ULVR.L",
        "dst": thesis["thesis_id"],
        "relation": "supports_thesis",
    }


def test_write_bundle_writes_all_main_payload_types():
    writer = _StubKGWriter()
    bridge = AIONEquitiesKGBridge(writer=writer)

    out = bridge.write_bundle(
        company={
            "company_id": "company/PAGE.L",
            "ticker": "PAGE.L",
            "name": "PageGroup",
        },
        assessment={
            "assessment_id": "assessment/company/PAGE.L/2026-03-01",
            "entity_id": "company/PAGE.L",
        },
        thesis={
            "thesis_id": "thesis/PAGE.L/long/bootstrap",
            "ticker": "PAGE.L",
            "company_ref": "company/PAGE.L",
            "assessment_refs": ["assessment/company/PAGE.L/2026-03-01"],
        },
        trigger_map={
            "company_trigger_map_id": "company/PAGE.L/trigger_map/2026Q1",
            "company_ref": "company/PAGE.L",
        },
        pre_earnings_estimate={
            "pre_earnings_estimate_id": "company/PAGE.L/pre_earnings/2026Q1",
            "company_ref": "company/PAGE.L",
        },
    )

    assert len(out["nodes"]) == 5
    assert len(writer.nodes) == 5
    assert len(writer.edges) == 5