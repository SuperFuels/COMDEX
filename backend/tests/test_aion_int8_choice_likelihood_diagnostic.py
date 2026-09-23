import torch

from backend.scripts.run_aion_int8_choice_likelihood_diagnostic import _select_choice


def test_select_choice_combines_bare_and_space_prefixed_spellings() -> None:
    logits = torch.full((20,), -10.0)
    token_ids = {"A": (1, 2), "B": (3, 4), "C": (5, 6), "D": (7, 8)}
    logits[1], logits[2] = 1.0, 1.0
    logits[3], logits[4] = 1.5, -10.0
    observed, scores, margin = _select_choice(logits, token_ids)
    assert observed == "A"
    assert scores["A"] > scores["B"]
    assert margin > 0
