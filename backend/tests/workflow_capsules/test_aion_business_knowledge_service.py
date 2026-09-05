from pathlib import Path
import io
import json
from datetime import UTC, datetime

import pytest
from zipfile import ZIP_DEFLATED, ZipFile

from backend.modules.aion_business.runtime.business_knowledge_service import BusinessKnowledgeService
from backend.modules.aion_business.runtime.department_context_assembler import _project_container


def _minimal_docx_bytes() -> bytes:
    document = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Home Fixed carbon-fibre carports use corrosion-resistant structural members.</w:t></w:r></w:p>
    <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Warranty</w:t></w:r></w:p></w:tc>
      <w:tc><w:p><w:r><w:t>Twenty-five years when installed to specification.</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
  </w:body>
</w:document>"""
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"/>")
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def test_company_knowledge_requires_owner_approval_and_keeps_provenance(tmp_path: Path):
    service = BusinessKnowledgeService(base_dir=tmp_path)
    result = service.ingest_text(
        "test-business",
        title="Fastener product facts",
        text="Our fasteners use Alloy X. They carry a fifty-year manufacturer warranty.",
        scopes=["sales", "marketing", "support", "products_services"],
        confidentiality="internal",
    )

    assert result["duplicate"] is False
    assert service.search("test-business", query="Alloy fasteners", actor_scope="sales")["matches"] == []

    claim_ids = [claim["claim_id"] for claim in result["claims"]]
    approved = service.approve("test-business", claim_ids=claim_ids, actor="owner")
    assert approved["approved_count"] == len(claim_ids)

    recalled = service.search("test-business", query="Alloy fasteners", actor_scope="sales")
    assert recalled["matches"]
    assert recalled["matches"][0]["verification_status"] == "owner_attested"
    assert recalled["matches"][0]["source_hash"] == result["source"]["source_hash"]
    assert recalled["receipt"]["claim_ids"]


def test_confidential_knowledge_is_scoped_to_permitted_functions(tmp_path: Path):
    service = BusinessKnowledgeService(base_dir=tmp_path)
    result = service.ingest_text(
        "test-business",
        title="Payroll reserve",
        text="The protected payroll reserve is 75000 GBP.",
        scopes=["finance", "people", "boardroom"],
        confidentiality="confidential",
    )
    service.approve(
        "test-business",
        claim_ids=[claim["claim_id"] for claim in result["claims"]],
        actor="owner",
    )

    assert service.search("test-business", query="payroll reserve", actor_scope="finance")["matches"]
    assert service.search("test-business", query="payroll reserve", actor_scope="marketing")["matches"] == []


def test_duplicate_sources_are_not_ingested_twice(tmp_path: Path):
    service = BusinessKnowledgeService(base_dir=tmp_path)
    first = service.ingest_text(
        "test-business",
        title="Support policy",
        text="Refunds above 500 GBP require owner approval.",
        scopes=["support"],
    )
    second = service.ingest_text(
        "test-business",
        title="Support policy copy",
        text="Refunds above 500 GBP require owner approval.",
        scopes=["support"],
    )

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["source"]["source_hash"] == first["source"]["source_hash"]


def test_retrieval_excludes_prohibited_marketing_examples_even_if_approved(tmp_path: Path):
    service = BusinessKnowledgeService(base_dir=tmp_path)
    result = service.ingest_text(
        "test-business",
        title="Product positioning and prohibited wording",
        text=(
            "The core differentiator is the combination of a lightweight hybrid frame, "
            "modular repairability and a corrosion-resistant architectural finish. "
            "35% lighter than every competing carport. "
            "Patent protected or patented."
        ),
        scopes=["sales", "marketing", "support", "products_services"],
    )
    service.approve(
        "test-business",
        claim_ids=[claim["claim_id"] for claim in result["claims"]],
        actor="owner",
    )

    recalled = service.search(
        "test-business",
        query="What makes this carport different?",
        actor_scope="pilot",
        limit=12,
    )
    texts = [match["text"] for match in recalled["matches"]]
    assert any("core differentiator" in text for text in texts)
    assert not any("every competing" in text for text in texts)
    assert not any("Patent protected or patented" in text for text in texts)


def test_docx_ingestion_works_without_optional_word_runtime_and_reads_tables(tmp_path: Path):
    service = BusinessKnowledgeService(base_dir=tmp_path)
    result = service.ingest_file(
        "test-business",
        filename="Home Fixed product pack.docx",
        data=_minimal_docx_bytes(),
        scopes=["products_services", "sales", "support"],
    )

    extracted = " ".join(claim["text"] for claim in result["claims"])
    assert "carbon-fibre carports" in extracted
    assert "Twenty-five years" in extracted
    assert result["source"]["filename"] == "Home Fixed product pack.docx"


def test_business_map_projection_only_exposes_knowledge_to_approved_scopes():
    public_fact = {"fact_id": "public", "value": "shared operating fact"}
    finance_fact = {
        "fact_id": "finance-only",
        "value": "protected treasury limit",
        "classification": "owner_attested_business_knowledge",
        "scopes": ["finance", "boardroom"],
    }
    people_fact = {
        "fact_id": "people-only",
        "value": "approved onboarding rule",
        "classification": "owner_attested_business_knowledge",
        "scopes": ["people"],
    }
    business_map = {"facts": [public_fact, finance_fact, people_fact], "revision": 4}

    finance = _project_container("business_map", business_map, "finance")
    marketing = _project_container("business_map", business_map, "marketing")
    hr = _project_container("business_map", business_map, "hr")

    assert [fact["fact_id"] for fact in finance["facts"]] == ["public", "finance-only"]
    assert [fact["fact_id"] for fact in marketing["facts"]] == ["public"]
    assert [fact["fact_id"] for fact in hr["facts"]] == ["public", "people-only"]


def test_entity_linking_uses_only_approved_claims_and_explicit_boardroom_entities(tmp_path: Path):
    business_root = tmp_path / "test-business"
    business_root.mkdir(parents=True)
    (business_root / "business_identity.json").write_text(json.dumps({
        "id": "test-business.business_identity", "legal_name": "Example Holdings",
    }))
    (business_root / "business_structure.json").write_text(json.dumps({
        "services": [{"id": "service:solar", "name": "Solar Installation"}],
        "teams": [{"id": "team:sales", "name": "Sales Team"}],
        "human_agents": [{"name": "Missing identifier"}],
    }))
    service = BusinessKnowledgeService(base_dir=tmp_path)
    approved_source = service.ingest_text(
        "test-business", title="Operating note",
        text="The Sales Team qualifies every Solar Installation request.",
    )
    pending_source = service.ingest_text(
        "test-business", title="Unreviewed note", text="Example Holdings may enter France.",
    )
    service.approve(
        "test-business", [claim["claim_id"] for claim in approved_source["claims"]], actor="owner",
    )

    result = service.rebuild_entity_links("test-business", actor="owner")
    assert result["link_count"] == 2
    assert {link["entity_id"] for link in result["links"]} == {"service:solar", "team:sales"}
    assert all(link["match_type"] == "deterministic_exact_name" for link in result["links"])
    assert pending_source["claims"][0]["claim_id"] not in {link["claim_id"] for link in result["links"]}
    assert service.summary("test-business")["entity_link_count"] == 2
    assert service.rebuild_entity_links("test-business", actor="owner")["changed"] is False


def test_source_revocation_removes_raw_material_and_blocks_retrieval(tmp_path: Path):
    service = BusinessKnowledgeService(base_dir=tmp_path)
    result = service.ingest_text("test-business", title="Old policy", text="Refunds are accepted within thirty days.")
    claim_ids = [claim["claim_id"] for claim in result["claims"]]
    service.approve("test-business", claim_ids, actor="owner")
    source_id = result["source"]["source_id"]
    raw_path = Path(result["source"]["raw_local_path"])
    assert raw_path.exists()
    with pytest.raises(PermissionError, match="confirmation"):
        service.revoke_source("test-business", source_id, actor="owner")
    revoked = service.revoke_source("test-business", source_id, actor="owner", confirm_revoke=True, reason="Superseded")
    assert revoked["revoked_claim_count"] == len(claim_ids)
    assert not raw_path.exists()
    assert service.search("test-business", "refunds", actor_scope="support")["matches"] == []


def test_legal_hold_prevents_retention_revocation(tmp_path: Path):
    service = BusinessKnowledgeService(base_dir=tmp_path)
    held = service.ingest_text("test-business", title="Held", text="A legally preserved customer record.")
    expired = service.ingest_text("test-business", title="Expired", text="An expired operating note for archive removal.")
    past = "2025-01-01T00:00:00+00:00"
    service.set_source_policy("test-business", held["source"]["source_id"], actor="owner", legal_hold=True, retention_until=past)
    service.set_source_policy("test-business", expired["source"]["source_id"], actor="owner", retention_until=past)
    with pytest.raises(PermissionError, match="legal hold"):
        service.revoke_source("test-business", held["source"]["source_id"], actor="owner", confirm_revoke=True)
    sweep = service.apply_retention("test-business", actor="retention_worker", now=datetime(2026, 1, 1, tzinfo=UTC))
    assert sweep["revoked_source_ids"] == [expired["source"]["source_id"]]
    statuses = {item["source_id"]: item["status"] for item in service.summary("test-business")["sources"]}
    assert statuses[held["source"]["source_id"]] == "awaiting_owner_review"
    assert statuses[expired["source"]["source_id"]] == "revoked"
