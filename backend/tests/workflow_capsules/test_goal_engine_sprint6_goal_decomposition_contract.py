from backend.modules.aion.goal_engine.decomposition import (
    GOAL_DECOMPOSITION_SCHEMA_VERSION,
    SUB_GOAL_SCHEMA_VERSION,
    GoalDecompositionContract,
    SubGoalContract,
    build_goal_decomposition_preview,
    build_sub_goal_preview,
)


def test_goal_decomposition_schema_versions_are_locked():
    assert SUB_GOAL_SCHEMA_VERSION == "aion.goal_engine.sub_goal.v1"
    assert GOAL_DECOMPOSITION_SCHEMA_VERSION == "aion.goal_engine.goal_decomposition.v1"


def test_sub_goal_preview_preserves_parent_goal_and_confidence():
    sub_goal = SubGoalContract(
        sub_goal_id="sub_goal_research_001",
        parent_goal_id="goal_launch_001",
        title="Research target audience",
        objective="Identify primary buyer segments.",
        confidence=0.82,
        glyph_code="RS-001",
    )

    preview = build_sub_goal_preview(sub_goal)

    assert preview["schema_version"] == SUB_GOAL_SCHEMA_VERSION
    assert preview["trace_type"] == "sub_goal_preview"
    assert preview["sub_goal_id"] == "sub_goal_research_001"
    assert preview["parent_goal_id"] == "goal_launch_001"
    assert preview["confidence"] == 0.82
    assert preview["glyph_code"] == "RS-001"
    assert preview["dry_run_only"] is True
    assert preview["would_execute"] is False


def test_goal_decomposition_preview_preserves_bounded_sub_goals():
    contract = GoalDecompositionContract(
        decomposition_id="decomp_launch_001",
        parent_goal_id="goal_launch_001",
        parent_goal_title="Launch campaign",
        decomposition_strategy="sequential",
        max_depth=3,
        max_sub_goals=4,
        current_depth=1,
        sub_goals=[
            SubGoalContract(
                sub_goal_id="sub_goal_research_001",
                parent_goal_id="goal_launch_001",
                title="Research",
                objective="Research audience.",
                confidence=0.8,
                glyph_code="RS-001",
            ),
            SubGoalContract(
                sub_goal_id="sub_goal_marketing_001",
                parent_goal_id="goal_launch_001",
                title="Marketing draft",
                objective="Draft first campaign.",
                confidence=0.75,
                glyph_code="MK-001",
            ),
        ],
    )

    preview = build_goal_decomposition_preview(contract)

    assert preview["schema_version"] == GOAL_DECOMPOSITION_SCHEMA_VERSION
    assert preview["trace_type"] == "goal_decomposition_preview"
    assert preview["parent_goal_id"] == "goal_launch_001"
    assert preview["decomposition_strategy"] == "sequential"
    assert preview["sub_goal_count"] == 2
    assert preview["bounded"] is True
    assert preview["needs_human_review"] is False
    assert preview["blocked_reasons"] == []


def test_goal_decomposition_blocks_unsupported_strategy():
    contract = GoalDecompositionContract(
        decomposition_id="decomp_bad_strategy",
        parent_goal_id="goal_launch_001",
        parent_goal_title="Launch campaign",
        decomposition_strategy="autonomous_free_for_all",
        max_depth=3,
        max_sub_goals=4,
        current_depth=1,
        sub_goals=[],
    )

    preview = build_goal_decomposition_preview(contract)

    assert preview["bounded"] is False
    assert "unsupported_decomposition_strategy" in preview["blocked_reasons"]
    assert "unbounded_decomposition_blocked" in preview["blocked_reasons"]


def test_goal_decomposition_blocks_depth_and_sub_goal_excess():
    contract = GoalDecompositionContract(
        decomposition_id="decomp_too_large",
        parent_goal_id="goal_launch_001",
        parent_goal_title="Launch campaign",
        decomposition_strategy="parallel",
        max_depth=1,
        max_sub_goals=1,
        current_depth=2,
        sub_goals=[
            SubGoalContract(
                sub_goal_id="sub_goal_001",
                parent_goal_id="goal_launch_001",
                title="One",
                objective="One objective.",
            ),
            SubGoalContract(
                sub_goal_id="sub_goal_002",
                parent_goal_id="goal_launch_001",
                title="Two",
                objective="Two objective.",
            ),
        ],
    )

    preview = build_goal_decomposition_preview(contract)

    assert preview["bounded"] is False
    assert "max_depth_exceeded" in preview["blocked_reasons"]
    assert "max_sub_goals_exceeded" in preview["blocked_reasons"]
    assert "unbounded_decomposition_blocked" in preview["blocked_reasons"]


def test_goal_decomposition_requires_approval_for_high_risk_expansion():
    contract = GoalDecompositionContract(
        decomposition_id="decomp_high_risk",
        parent_goal_id="goal_finance_001",
        parent_goal_title="Move money",
        decomposition_strategy="review_gated",
        max_depth=2,
        max_sub_goals=3,
        current_depth=1,
        risk_tier="high",
        approval_required_before_expansion=False,
        sub_goals=[
            SubGoalContract(
                sub_goal_id="sub_goal_finance_001",
                parent_goal_id="goal_finance_001",
                title="Prepare finance action",
                objective="Draft finance action only.",
                confidence=0.7,
                glyph_code="FN-001",
                needs_human_review=True,
                risk_tier="high",
            ),
        ],
    )

    preview = build_goal_decomposition_preview(contract)

    assert preview["needs_human_review"] is True
    assert "high_risk_expansion_requires_approval" in preview["blocked_reasons"]
    assert preview["would_execute"] is False


def test_goal_decomposition_preview_preserves_sub_goal_previews():
    contract = GoalDecompositionContract(
        decomposition_id="decomp_preserve_previews",
        parent_goal_id="goal_ops_001",
        parent_goal_title="Improve operations",
        decomposition_strategy="sequential",
        max_depth=3,
        max_sub_goals=4,
        current_depth=1,
        sub_goals=[
            SubGoalContract(
                sub_goal_id="sub_goal_ops_001",
                parent_goal_id="goal_ops_001",
                title="Map current process",
                objective="Create process map.",
                confidence=0.9,
                glyph_code="OP-001",
            )
        ],
    )

    preview = build_goal_decomposition_preview(contract)

    assert "sub_goal_previews" in preview
    assert len(preview["sub_goal_previews"]) == 1
    assert preview["sub_goal_previews"][0]["sub_goal_id"] == "sub_goal_ops_001"
    assert preview["sub_goal_previews"][0]["glyph_code"] == "OP-001"
