from pathlib import Path


BRIDGE = Path("backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py")
PREVIEW_BUNDLE = Path("backend/modules/aion/goal_engine/preview_bundle.py")
APP = Path("desktop/mac/src/app.js")


def test_goal_runtime_summary_is_built_inside_preview_bundle_only():
    preview_text = PREVIEW_BUNDLE.read_text()
    bridge_text = BRIDGE.read_text()

    assert "def _build_goal_runtime_summary(" in preview_text
    assert "goal_runtime_summary = _build_goal_runtime_summary(" in preview_text

    # Bridge may attach/mirror the summary, but must not build its own competing summary.
    assert "def _build_goal_runtime_summary(" not in bridge_text
    assert "goal_runtime_summary = _build_goal_runtime_summary(" not in bridge_text


def test_bridge_only_reads_goal_runtime_summary_from_bundle_payload():
    text = BRIDGE.read_text()

    assert 'canonical_goal_runtime_summary = bundle_payload.get("goal_runtime_summary")' in text
    assert 'payload["goal_runtime_summary"] = canonical_goal_runtime_summary' in text
    assert 'payload["goal_engine_goal_runtime_summary"] = canonical_goal_runtime_summary' in text


def test_boardroom_ui_reads_summary_without_recomputing_it():
    text = APP.read_text()

    assert "function getAionGoalEngineRuntimeSummaryV1" in text
    assert "function renderAionGoalEngineRuntimeSummaryBoardroomV1" in text

    # UI may display the summary, but must not compute canonical scoring/runtime policy.
    forbidden_fragments = [
        "function buildGoalRuntimeSummary",
        "function _buildGoalRuntimeSummary",
        "premature_convergence_blocked =",
        "outcome_success_requires_evidence =",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in text


def test_sprint2_canonical_visibility_contract_terms_are_present():
    text = PREVIEW_BUNDLE.read_text() + "\n" + BRIDGE.read_text() + "\n" + APP.read_text()

    required = [
        "goal_runtime_summary",
        "outcome_success_requires_evidence",
        "premature_convergence_blocked",
        "bounded_loop_count",
        "unbounded_loop_count",
        "human_approval_required",
        "commercial_interface_ready",
        "agent_ready",
    ]

    for term in required:
        assert term in text
