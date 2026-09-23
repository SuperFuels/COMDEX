from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    attach_goal_engine_manifest_to_dry_result,
    build_goal_engine_learning_reflection_preview,
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
)


class DummyDryResult:
    def to_dict(self):
        return {
            "schema_version": "aion.workflow_capsule_dry_run_result.v1",
            "status": "dry_run_completed",
            "trace": [],
        }


def learning_capsule(allow_learn=True, adr_active=False):
    return {
        "canonical_key": "test.goal_engine.learning_reflection_preview",
        "steps": [
            {
                "id": "goal_1",
                "title": "Improve lead quality",
                "action_id": "goal_engine.goal",
                "config": {
                    "allow_learn": allow_learn,
                    "adr_active": adr_active,
                    "winning_patterns": ["shorter WhatsApp opener"],
                    "failed_patterns": ["generic long pitch"],
                    "memory_confidence": 0.72,
                    "memory_provenance": "run:lead_quality_001",
                },
            },
            {
                "id": "reflect_1",
                "title": "Reflect and learn",
                "action_id": "goal_engine.reflect_learn",
                "config": {
                    "allow_learn": allow_learn,
                    "adr_active": adr_active,
                    "reflection_summary": "Shorter local messages performed better.",
                    "winning_patterns": ["local proof", "single clear CTA"],
                    "failed_patterns": ["too much detail before trust"],
                    "episodic_memory": "run summary only",
                    "semantic_glyph_memory": "local lead opener pattern",
                    "memory_confidence": 0.81,
                    "memory_provenance": "workflow:test.goal_engine.learning_reflection_preview",
                },
            },
        ],
    }


def test_build_learning_reflection_preview_directly():
    preview = build_goal_engine_learning_reflection_preview(
        {
            "node_id": "reflect_1",
            "node_kind": "reflect_learn",
            "payload": {
                "allow_learn": True,
                "adr_active": False,
                "reflection_summary": "Local proof won.",
                "winning_patterns": ["local proof"],
                "failed_patterns": ["generic copy"],
                "memory_confidence": 0.77,
                "memory_provenance": "run:test",
            },
        },
        run_id="run_learning_1",
    )

    assert preview["schema_version"] == "aion.goal_engine.learning_reflection_preview.v1"
    assert preview["node_id"] == "reflect_1"
    assert preview["allow_learn"] is True
    assert preview["adr_active"] is False
    assert preview["would_write_memory"] is True
    assert preview["learned_memory_grants_permission"] is False
    assert preview["can_execute_from_memory"] is False
    assert preview["memory_confidence"] == 0.77
    assert preview["winning_patterns"] == ["local proof"]
    assert preview["failed_patterns"] == ["generic copy"]


def test_step_trace_rows_include_learning_reflection_preview():
    manifest = build_goal_engine_manifest_for_capsule(
        learning_capsule(allow_learn=True, adr_active=False),
        run_id="run_learning_2",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_learning_2")

    reflect_row = next(row for row in rows if row["node_kind"] in {"reflect_learn", "reflection", "learn"})
    preview = reflect_row["learning_reflection_preview"]

    assert preview["allow_learn"] is True
    assert preview["would_write_memory"] is True
    assert preview["bridge_to_prior_bank"] is True
    assert preview["learning_blocked_reason"] == ""
    assert preview["reflection_summary"] == "Shorter local messages performed better."
    assert reflect_row["payload"]["learning_reflection_preview"]["semantic_glyph_memory"] == "local lead opener pattern"


def test_learning_reflection_blocks_when_adr_active():
    manifest = build_goal_engine_manifest_for_capsule(
        learning_capsule(allow_learn=True, adr_active=True),
        run_id="run_learning_3",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_learning_3")

    reflect_row = next(row for row in rows if row["node_kind"] in {"reflect_learn", "reflection", "learn"})
    preview = reflect_row["learning_reflection_preview"]

    assert preview["allow_learn"] is True
    assert preview["adr_active"] is True
    assert preview["would_write_memory"] is False
    assert preview["bridge_to_prior_bank"] is False
    assert preview["learning_blocked_reason"] == "adr_active"


def test_learning_reflection_blocks_without_allow_learn():
    preview = build_goal_engine_learning_reflection_preview(
        {
            "node_id": "reflect_2",
            "payload": {
                "allow_learn": False,
                "adr_active": False,
                "winning_patterns": ["x"],
            },
        },
        run_id="run_learning_4",
    )

    assert preview["allow_learn"] is False
    assert preview["would_write_memory"] is False
    assert preview["bridge_to_prior_bank"] is False
    assert preview["learning_blocked_reason"] == "allow_learn_false"


def test_manifest_attach_preserves_learning_reflection_preview_in_trace():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        learning_capsule(allow_learn=True, adr_active=False),
        run_id="run_learning_5",
    )

    payload = result.to_dict()
    reflect_row = next(row for row in payload["trace"] if row.get("node_kind") in {"reflect_learn", "reflection", "learn"})

    assert reflect_row["learning_reflection_preview"]["schema_version"] == "aion.goal_engine.learning_reflection_preview.v1"
    assert reflect_row["learning_reflection_preview"]["would_write_memory"] is True
    assert reflect_row["learning_reflection_preview"]["learned_memory_grants_permission"] is False
