from pathlib import Path


BRIDGE = Path("backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py")


def test_bridge_attaches_resume_revalidation_summary_from_bundle():
    text = BRIDGE.read_text()

    assert 'canonical_resume_revalidation_summary = bundle_payload.get("resume_revalidation_summary")' in text
    assert 'setattr(dry_result, "goal_engine_resume_revalidation_summary", canonical_resume_revalidation_summary)' in text
    assert 'setattr(dry_result, "resume_revalidation_summary", canonical_resume_revalidation_summary)' in text


def test_bridge_payload_exposes_resume_revalidation_summary_legacy_mirror():
    text = BRIDGE.read_text()

    assert 'payload["goal_engine_resume_revalidation_summary"] = canonical_resume_revalidation_summary' in text
    assert 'payload["resume_revalidation_summary"] = canonical_resume_revalidation_summary' in text


def test_bridge_does_not_rebuild_resume_revalidation_summary():
    text = BRIDGE.read_text()
    marker = "# AION PATCH: Goal Engine canonical preview bundle bridge final override v13"

    assert marker in text
    section = text[text.index(marker):]

    assert "build_resume_revalidation_preview(" not in section
    assert "_build_resume_revalidation_summary(" not in section
    assert "ResumeRevalidationContract(" not in section
