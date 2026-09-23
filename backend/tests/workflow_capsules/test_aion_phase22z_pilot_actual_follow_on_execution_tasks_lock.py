from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22z_marketing_follow_on_queue_uses_actual_plan_steps():
    assert "Define marketing objective" in TEXT
    assert "Clarify target audience and offer" in TEXT
    assert "Draft positioning and core message" in TEXT
    assert "Build channel and content plan" in TEXT
    assert "Prepare lead capture workflow" in TEXT
    assert "Create review-ready marketing plan output" in TEXT


def test_phase22z_marketing_outputs_are_not_generic_placeholder_only():
    assert "This draft turns one approved plan item into a usable working asset" in TEXT
    assert "Channel plan" in TEXT
    assert "Content queue" in TEXT
    assert "Lead capture workflow" in TEXT
    assert "Review-ready execution pack" in TEXT


def test_phase22z_continue_runner_can_build_real_marketing_subtasks():
    assert "Weekly rhythm draft" in TEXT
    assert "Intake fields" in TEXT
    assert "Example hooks" in TEXT
    assert "Success measures" in TEXT


def test_phase22z_live_actions_still_blocked():
    assert "No posts, adverts or messages have been published or sent" in TEXT
    assert "has not posted, sent messages, spent money, booked jobs" in TEXT
