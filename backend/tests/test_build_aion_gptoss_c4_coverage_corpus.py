from backend.scripts.build_aion_gptoss_c4_coverage_corpus import PROMPTS, SPLITS


def test_c4_coverage_corpus_has_disjoint_frozen_splits() -> None:
    assert set(PROMPTS) == {
        "arithmetic", "business", "explanation", "extraction", "reasoning", "writing",
    }
    assert SPLITS.count("training") == 4
    assert SPLITS.count("selection") == 1
    assert SPLITS.count("holdout") == 1
    assert all(len(prompts) == len(SPLITS) for prompts in PROMPTS.values())
    assert len({prompt for prompts in PROMPTS.values() for prompt in prompts}) == 36


def test_c4_coverage_prompts_are_generic_and_nonempty() -> None:
    assert all(prompt.strip() for prompts in PROMPTS.values() for prompt in prompts)
