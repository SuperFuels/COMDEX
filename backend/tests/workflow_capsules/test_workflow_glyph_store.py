from __future__ import annotations

from pathlib import Path

from backend.modules.workflow_capsules.glyph_store.workflow_glyph_schema import (
    WorkflowGlyph,
    stable_glyph_code,
)
from backend.modules.workflow_capsules.glyph_store.workflow_glyph_repository import (
    WorkflowGlyphRepository,
)


def _repo(tmp_path: Path) -> WorkflowGlyphRepository:
    return WorkflowGlyphRepository(
        glyph_dir=tmp_path / "glyphs",
        index_path=tmp_path / "workflow_glyph_index.json",
    )


def _glyph(code: str = "GM-1001", *, scope: str = "my", callable: bool = True) -> WorkflowGlyph:
    return WorkflowGlyph.from_dict({
        "glyph_id": f"glyph.{code.lower()}",
        "glyph_code": code,
        "name": "Gmail Customer Enquiry Reply",
        "workflow_id": "workflow:gmail.enquiry_reply.v1",
        "workflow_version": "v1",
        "glyph_version": "v1",
        "scope": scope,
        "callable": callable,
        "input_schema": {
            "type": "object",
            "properties": {
                "gmail_message_id": {"type": "string"},
            },
            "required": ["gmail_message_id"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "draft_reply": {"type": "string"},
            },
        },
        "required_connectors": ["gmail"],
        "risk_tier": "medium",
        "approval_policy": {
            "requires_human_approval": True,
            "external_write": False,
        },
        "runtime_plan": {
            "mode": "dry_run",
            "steps": ["read_email", "extract_enquiry_intent", "draft_reply"],
        },
        "tags": ["gmail", "email", "customer"],
    })


def test_workflow_glyph_contract_finalizes_with_hashes() -> None:
    glyph = _glyph()

    assert glyph.glyph_code == "GM-1001"
    assert glyph.glyph_id == "glyph.gm-1001"
    assert glyph.callable is True
    assert glyph.meta["schema_version"] == "aion.workflow_glyph_store.v1"
    assert glyph.meta["checksum"]
    assert glyph.meta["version_hash"]
    assert glyph.version_hash() == glyph.meta["version_hash"]


def test_stable_glyph_code_is_deterministic() -> None:
    a = stable_glyph_code("workflow:gmail.enquiry_reply.v1", prefix="GM")
    b = stable_glyph_code("workflow:gmail.enquiry_reply.v1", prefix="GM")

    assert a == b
    assert a.startswith("GM-")
    assert len(a) == 7


def test_workflow_glyph_repository_save_load_and_index(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    glyph = _glyph()

    saved = repo.save(glyph)

    assert saved["ok"] is True
    assert Path(saved["path"]).exists()

    loaded = repo.require("GM-1001", "v1")
    assert loaded.glyph_code == "GM-1001"
    assert loaded.workflow_id == "workflow:gmail.enquiry_reply.v1"
    assert loaded.required_connectors == ["gmail"]

    assert (tmp_path / "workflow_glyph_index.json").exists()


def test_workflow_glyph_repository_search_scope_and_callable_filter(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    repo.save(_glyph("GM-1001", scope="my", callable=True))
    repo.save(_glyph("GM-1002", scope="universal", callable=True))
    repo.save(_glyph("GM-1003", scope="my", callable=False))

    all_gmail = repo.search("gmail")
    assert len(all_gmail) == 3

    my_callable = repo.search("gmail", scope="my", callable_only=True)
    assert [g.glyph_code for g in my_callable] == ["GM-1001"]

    universal = repo.search("gmail", scope="universal", callable_only=True)
    assert [g.glyph_code for g in universal] == ["GM-1002"]


def test_workflow_glyph_repository_latest_version_lookup(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    v1 = _glyph("GM-2001")
    v1.glyph_version = "v1"
    repo.save(v1)

    v2 = _glyph("GM-2001")
    v2.glyph_version = "v2"
    v2.name = "Gmail Customer Enquiry Reply v2"
    repo.save(v2)

    latest = repo.require("GM-2001")
    assert latest.glyph_version == "v2"
    assert latest.name.endswith("v2")

    pinned = repo.require("GM-2001", "v1")
    assert pinned.glyph_version == "v1"
