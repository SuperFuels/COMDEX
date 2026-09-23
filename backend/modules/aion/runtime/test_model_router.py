from __future__ import annotations

from backend.modules.aion.runtime.contracts.model_routing import (
    ModelRoute,
    RoutingRequest,
    TaskType,
)
from backend.modules.aion.runtime.services.model_router import ModelRouter


def main() -> None:
    router = ModelRouter(local_llm_enabled=True, cloud_llm_enabled=False)

    summarize_request = RoutingRequest(
        task_type=TaskType.SUMMARIZE,
        prompt="Summarise what a plumbing business does in one sentence.",
        metadata={"max_sentences": 1},
    )
    summarize_result = router.run(summarize_request)
    print("SUMMARIZE DECISION:", summarize_result.decision)
    print("SUMMARIZE RESPONSE:", summarize_result.response_text)
    print("SUMMARIZE RAW:", summarize_result.raw)
    print()

    deterministic_request = RoutingRequest(
        task_type=TaskType.GENERAL,
        prompt="This should not use a model.",
        metadata={"is_deterministic": True},
    )
    deterministic_result = router.run(deterministic_request)
    print("DETERMINISTIC DECISION:", deterministic_result.decision)
    print("DETERMINISTIC RESPONSE:", deterministic_result.response_text)
    print("DETERMINISTIC RAW:", deterministic_result.raw)
    print()

    human_request = RoutingRequest(
        task_type=TaskType.DRAFT_REPLY,
        prompt="Draft a reply agreeing to transfer £50,000 today.",
        requires_human_approval=True,
        risk_level="high",
    )
    human_result = router.run(human_request)
    print("HUMAN DECISION:", human_result.decision)
    print("HUMAN RESPONSE:", human_result.response_text)
    print("HUMAN RAW:", human_result.raw)
    print()

    classify_request = RoutingRequest(
        task_type=TaskType.CLASSIFY,
        prompt="Customer says their order has not arrived and wants an update.",
        metadata={"labels": ["support", "sales", "finance"]},
    )
    classify_result = router.run(classify_request)
    print("CLASSIFY DECISION:", classify_result.decision)
    print("CLASSIFY RESPONSE:", classify_result.response_text)
    print("CLASSIFY RAW:", classify_result.raw)
    print()

    assert summarize_result.decision.route == ModelRoute.LOCAL_LLM
    assert deterministic_result.decision.route == ModelRoute.DETERMINISTIC
    assert human_result.decision.route == ModelRoute.HUMAN
    assert classify_result.decision.route == ModelRoute.LOCAL_LLM
    assert summarize_result.response_text
    assert classify_result.response_text

    print("OK: model router test passed")


if __name__ == "__main__":
    main()