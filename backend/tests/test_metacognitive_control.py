from backend.modules.hexcore.metacognitive_control import MetacognitiveController


def test_cheap_review_allows_reversible_low_risk_action():
    review=MetacognitiveController().review(goal={"goal_id":"g","risk_tier":"low"},investigation={},learned_context={},plan={},action={"action_id":"a","type":"read","risk_tier":"low","executable":True,"reversible":True},history=[])
    assert review["decision"] == "execute"
    assert review["depth"] == "cheap"


def test_deep_review_revises_counterfactually_invalidated_action():
    primary={"action_id":"capture","type":"chess_move","risk_tier":"high","executable":True,"predicted_success":.8,"worst_case_loss":.9,"reversible":False,"verification_plan":"simulate reply"}
    alternative={"action_id":"defend","predicted_success":.75,"worst_case_loss":.1,"reversible":True}
    review=MetacognitiveController().review(goal={"goal_id":"g"},investigation={},learned_context={},plan={"counterfactuals":[{"invalidates_action":True,"reason":"opponent mate"}],"alternatives":[alternative]},action=primary,history=[])
    assert review["decision"] == "revise"
    assert review["revised_action"]["action_id"] == "defend"
    assert review["depth"] == "deep"


def test_irreversible_unverified_action_is_stopped():
    review=MetacognitiveController().review(goal={"goal_id":"g"},investigation={},learned_context={},plan={},action={"action_id":"deploy","type":"deployment","risk_tier":"critical","executable":True,"irreversible":True},history=[])
    assert review["decision"] == "investigate"


def test_bad_outcome_creates_narrow_assumption_lesson_used_next_time():
    controller = MetacognitiveController()
    action = {
        "action_id": "walk_without_checking",
        "type": "walking_step",
        "risk_tier": "low",
        "executable": True,
        "reversible": True,
        "predicted_success": 0.95,
        "assumptions": ["the path ahead is unobstructed"],
    }
    initial = controller.review(
        goal={"goal_id": "walk-1"},
        investigation={},
        learned_context={},
        plan={},
        action=action,
        history=[],
    )
    reflection = controller.reflect_outcome(
        goal={"goal_id": "walk-1"},
        plan={},
        action=action,
        review=initial,
        action_result={"status": "executed"},
        observation={"verified": False, "score": 0.0},
        criticism={"failure_type": "outcome"},
    )
    assert reflection["outcome_grade"] == "bad"
    assert reflection["attribution"] == "assumption"
    assert reflection["lesson"]["failed_assumption"] == "the path ahead is unobstructed"
    assert reflection["lesson"]["scope"] == "matching_decision_signature_only"

    second = controller.review(
        goal={"goal_id": "walk-2"},
        investigation={},
        learned_context={},
        plan={},
        action=action,
        history=[{
            "action_signature": initial["action_signature"],
            "verified": False,
            "outcome_grade": "bad",
            "outcome_reflection": reflection,
        }],
    )
    assert second["depth"] == "deep"
    assert "counterexample_search" in second["checks"]
    assert second["learned_lessons"][0]["attribution"] == "assumption"


def test_routine_expected_success_skips_post_action_reflection():
    controller = MetacognitiveController()
    action = {
        "action_id": "read",
        "type": "read",
        "risk_tier": "low",
        "executable": True,
        "reversible": True,
        "predicted_success": 0.95,
    }
    review = controller.review(
        goal={"goal_id": "g"}, investigation={}, learned_context={}, plan={},
        action=action, history=[]
    )
    reflection = controller.reflect_outcome(
        goal={"goal_id": "g"}, plan={}, action=action, review=review,
        action_result={"status": "executed"},
        observation={"verified": True, "score": 1.0},
        criticism={"failure_type": "none"},
    )
    assert reflection["performed"] is False
    assert reflection["cheap_noop"] is True
    assert reflection["lesson"] is None
    assert reflection["llm_calls"] == 0


def test_execution_failure_does_not_blame_decision_assumption():
    controller = MetacognitiveController()
    action = {
        "action_id": "run-tool",
        "type": "tool",
        "risk_tier": "medium",
        "executable": True,
        "reversible": True,
        "assumptions": ["the intended method is correct"],
    }
    review = controller.review(
        goal={"goal_id": "g"}, investigation={}, learned_context={}, plan={},
        action=action, history=[]
    )
    reflection = controller.reflect_outcome(
        goal={"goal_id": "g"}, plan={}, action=action, review=review,
        action_result={"status": "failed", "error": "missing adapter"},
        observation={"verified": False, "score": 0.0},
        criticism={"failure_type": "execution"},
    )
    assert reflection["attribution"] == "execution"
    assert reflection["lesson"]["recommended_adjustment"] == "repair_or_replace_execution_path_before_retry"
