from backend.modules.aion.goal_engine.boardroom_trace import build_goal_engine_boardroom_trace
from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
)


def learning_feedback_capsule(allow_learn=True, adr_active=False):
    return {
        "canonical_key": "test.goal_engine.boardroom_learning_feedback_visibility",
        "steps": [
            {
                "id": "goal_1",
                "title": "Improve CostaConnect lead quality",
                "action_id": "goal_engine.goal",
                "config": {
                    "feedback_required": True,
                    "feedback_category": "lead_quality",
                    "allow_learning": False,
                    "do_not_learn_from_this": True,
                },
            },
            {
                "id": "reflect_1",
                "title": "Reflect and learn",
                "action_id": "goal_engine.reflect_learn",
                "config": {
                    "allow_learn": allow_learn,
                    "adr_active": adr_active,
                    "reflection_summary": "Short local WhatsApp messages performed better.",
                    "winning_patterns": ["local proof", "single CTA"],
                    "failed_patterns": ["generic long pitch"],
                    "semantic_glyph_memory": "local lead opener pattern",
                    "memory_confidence": 0.82,
                    "memory_provenance": "run:lead_quality_001",
                },
            },
        ],
    }


def boardroom_trace_for_capsule(capsule):
    manifest = build_goal_engine_manifest_for_capsule(capsule, run_id="run_boardroom_learning_1")
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_boardroom_learning_1")
    manifest["goal_engine_step_trace"] = rows
    manifest["trace"] = rows
    return build_goal_engine_boardroom_trace(manifest)


def test_boardroom_trace_exposes_learning_summary():
    trace = boardroom_trace_for_capsule(learning_feedback_capsule())

    assert "learning_summary" in trace
    learning = trace["learning_summary"]

    assert learning["schema_version"] == "aion.goal_engine.boardroom_learning_summary.v1"
    assert learning["would_write_memory_count"] == 1
    assert learning["learned_memory_grants_permission"] is False
    assert learning["can_execute_from_memory"] is False
    assert "Short local WhatsApp messages performed better." in learning["reflection_summaries"]
    assert "local proof" in learning["winning_patterns"]
    assert "generic long pitch" in learning["failed_patterns"]
    assert learning["memory_confidence_max"] == 0.82


def test_boardroom_trace_exposes_learning_blockers():
    trace = boardroom_trace_for_capsule(
        learning_feedback_capsule(allow_learn=True, adr_active=True),
    )

    learning = trace["learning_summary"]

    assert learning["would_write_memory_count"] == 0
    assert "adr_active" in learning["learning_blocked_reasons"]
    assert learning["learned_memory_grants_permission"] is False
    assert learning["can_execute_from_memory"] is False


def test_boardroom_trace_exposes_human_feedback_summary():
    trace = boardroom_trace_for_capsule(learning_feedback_capsule())

    assert "human_feedback_summary" in trace
    feedback = trace["human_feedback_summary"]

    assert feedback["schema_version"] == "aion.goal_engine.boardroom_human_feedback_summary.v1"
    assert feedback["feedback_required_count"] >= 1
    assert "lead_quality" in feedback["feedback_categories"]
    assert feedback["negative_feedback_grants_permission"] is False
    assert feedback["allow_learning_count"] == 0
    assert feedback["do_not_learn_count"] >= 1


def test_boardroom_visibility_fields_include_learning_and_feedback():
    trace = boardroom_trace_for_capsule(learning_feedback_capsule())

    fields = trace.get("boardroom_visibility_fields", [])

    assert "learning_summary" in fields
    assert "human_feedback_summary" in fields

    event_text = str(trace.get("events", []))
    assert "goal_engine.learning_visible" in event_text
    assert "goal_engine.human_feedback_visible" in event_text
