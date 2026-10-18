from __future__ import annotations

from pathlib import Path
import json
import tempfile

from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    WorkflowCapsule,
    make_workflow_capsule,
)
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import (
    WorkflowCapsuleRepository,
)
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import (
    WorkflowGlyphRegistry,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_expander import (
    WorkflowCapsuleExpander,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_policy import (
    WorkflowCapsulePolicyGate,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_dry_run import (
    WorkflowCapsuleDryRunExecutor,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_trace import (
    WorkflowCapsuleTraceWriter,
)
from backend.modules.workflow_capsules.resonance.workflow_capsule_feedback import (
    WorkflowCapsuleFeedbackEngine,
)


CORE_KEY = "workflow:gmail.enquiry_reply.v1"
CORE_PATH = "data/workflow_capsules/core/gmail_enquiry_reply.workflow.wiki.phn"


def _load_core_capsule():
    return WorkflowCapsule.load(CORE_PATH)


def _cau(allow: bool):
    return {
        "allow_learn": allow,
        "adr_active": False,
        "deny_reason": None if allow else "test_cau_denied",
    }


def test_workflow_capsule_save_load_round_trip_preserves_fields():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "gmail.workflow.wiki.phn"

        c = make_workflow_capsule(
            canonical_key=CORE_KEY,
            display_name="Handle Gmail Enquiry",
            meaning="Draft a Gmail enquiry reply, pause for approval, then allow approved send later.",
            display_glyph="WG-001",
            tags=["gmail", "approval", "draft_email"],
            vault_requirements=["vault.gmail.credentials"],
            workflow_graph={"nodes": [], "edges": []},
            compiled_glyph={"schema_version": "aion.workflow_glyph.v1", "steps": []},
        )
        c.save(path)

        loaded = WorkflowCapsule.load(path)

        assert loaded.canonical_key == c.canonical_key
        assert loaded.display_name == c.display_name
        assert loaded.policy.dry_run_first is True
        assert loaded.vault_requirements == ["vault.gmail.credentials"]
        assert loaded.compiled_glyph["schema_version"] == "aion.workflow_glyph.v1"
        assert loaded.checksum() == loaded.meta["checksum"]


def test_repository_can_require_seeded_gmail_capsule():
    repo = WorkflowCapsuleRepository()
    capsule = repo.require(CORE_KEY)

    assert capsule.canonical_key == CORE_KEY
    assert capsule.display_name == "Handle Gmail Enquiry"
    assert capsule.policy.dry_run_first is True
    assert "vault.gmail.credentials" in capsule.vault_requirements


def test_glyph_registry_resolves_key_glyph_tag_alias_and_semantic_text():
    reg = WorkflowGlyphRegistry()
    result = reg.rebuild_and_save()

    assert result["ok"] is True
    assert result["build"]["count"] >= 1

    assert reg.require(CORE_KEY).canonical_key == CORE_KEY
    assert reg.require("WG-001").canonical_key == CORE_KEY
    assert reg.find("gmail")[0].canonical_key == CORE_KEY
    assert reg.find("Handle Gmail Enquiry")[0].canonical_key == CORE_KEY
    assert reg.find("draft gmail enquiry reply")[0].canonical_key == CORE_KEY


def test_expander_expands_seeded_gmail_capsule_to_five_steps():
    capsule = _load_core_capsule()
    result = WorkflowCapsuleExpander().expand(capsule)

    assert result.ok is True
    assert result.errors == []
    assert result.warnings == []
    assert len(result.steps) == 5

    assert [s.step_id for s in result.steps] == [
        "read_email",
        "extract_enquiry_intent",
        "draft_reply",
        "approval_checkpoint",
        "send_email_after_approval",
    ]

    assert result.steps[-1].external_write is True
    assert result.steps[-1].requires_approval is True


def test_policy_gate_blocks_missing_vault_and_external_write_in_dry_run():
    capsule = _load_core_capsule()
    expansion = WorkflowCapsuleExpander().expand(capsule)

    policy = WorkflowCapsulePolicyGate().evaluate(
        capsule,
        expansion,
        available_vault_requirements=[],
        cau_state=_cau(False),
        phase="dry_run",
    )

    assert policy.ok is True
    assert policy.external_writes_present is True
    assert policy.external_writes_allowed_now is False
    assert policy.missing_vault_requirements == ["vault.gmail.credentials"]

    blocked_ids = {s["step_id"] for s in policy.blocked_steps}
    assert "read_email" in blocked_ids
    assert "send_email_after_approval" in blocked_ids

    assert any("CAU allow_learn=false" in w for w in policy.warnings)


def test_dry_run_simulates_safe_steps_and_blocks_external_write():
    capsule = _load_core_capsule()
    expansion = WorkflowCapsuleExpander().expand(capsule)

    dry = WorkflowCapsuleDryRunExecutor().run(
        capsule,
        expansion,
        available_vault_requirements=[],
        cau_state=_cau(False),
        inputs={"gmail_message_id": "demo-message-001"},
    )

    assert dry.ok is True
    assert dry.approval_required is True
    assert dry.external_writes_blocked is True
    assert dry.errors == []

    by_id = {s.step_id: s for s in dry.steps}

    assert by_id["read_email"].status == "blocked"
    assert by_id["extract_enquiry_intent"].status == "simulated"
    assert by_id["draft_reply"].status == "simulated"
    assert by_id["approval_checkpoint"].status == "simulated"
    assert by_id["send_email_after_approval"].status == "blocked"


def test_trace_writer_appends_execution_log_jsonl(tmp_path: Path):
    capsule = _load_core_capsule()
    expansion = WorkflowCapsuleExpander().expand(capsule)

    cau_state = _cau(False)
    policy = WorkflowCapsulePolicyGate().evaluate(
        capsule,
        expansion,
        available_vault_requirements=[],
        cau_state=cau_state,
        phase="dry_run",
    )
    dry = WorkflowCapsuleDryRunExecutor().run(
        capsule,
        expansion,
        available_vault_requirements=[],
        cau_state=cau_state,
        inputs={"gmail_message_id": "demo-message-001"},
    )

    log_path = tmp_path / "workflow_execution_log.jsonl"
    out = WorkflowCapsuleTraceWriter(path=log_path).append(
        event_type="dry_run_completed",
        capsule=capsule,
        expansion_result=expansion,
        policy_result=policy,
        run_result=dry,
        cau_state=cau_state,
        extra={"test": True},
    )

    assert out["ok"] is True
    assert log_path.exists()

    row = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert row["schema_version"] == "aion.workflow_execution_log.v1"
    assert row["canonical_key"] == CORE_KEY
    assert row["run_id"] == dry.run_id
    assert row["trace_hash"]


def test_feedback_does_not_mutate_capsule_when_cau_denies(tmp_path: Path):
    capsule = _load_core_capsule()
    before = capsule.meta["checksum"]

    expansion = WorkflowCapsuleExpander().expand(capsule)
    dry = WorkflowCapsuleDryRunExecutor().run(
        capsule,
        expansion,
        available_vault_requirements=[],
        cau_state=_cau(False),
        inputs={"gmail_message_id": "demo-message-001"},
    )

    out = WorkflowCapsuleFeedbackEngine(path=tmp_path / "feedback.jsonl").apply(
        capsule=capsule,
        run_result=dry,
        cau_state=_cau(False),
        persist_capsule=False,
    )

    assert out["ok"] is True
    assert out["mutation_allowed"] is False
    assert out["mutation_applied"] is False
    assert capsule.meta["checksum"] == before
    assert capsule.meta.get("sqi_score") == 0.0


def test_feedback_mutates_capsule_when_cau_allows(tmp_path: Path):
    capsule = _load_core_capsule()
    before = capsule.meta["checksum"]

    expansion = WorkflowCapsuleExpander().expand(capsule)
    dry = WorkflowCapsuleDryRunExecutor().run(
        capsule,
        expansion,
        available_vault_requirements=[],
        cau_state=_cau(True),
        inputs={"gmail_message_id": "demo-message-001"},
    )

    out = WorkflowCapsuleFeedbackEngine(path=tmp_path / "feedback.jsonl").apply(
        capsule=capsule,
        run_result=dry,
        cau_state=_cau(True),
        persist_capsule=False,
    )

    assert out["ok"] is True
    assert out["mutation_allowed"] is True
    assert out["mutation_applied"] is True
    assert capsule.meta["checksum"] != before
    assert capsule.meta.get("sqi_score", 0.0) > 0.0
    assert capsule.meta.get("ρ", 0.0) > 0.0
    assert capsule.meta.get("Ī", 0.0) > 0.0
