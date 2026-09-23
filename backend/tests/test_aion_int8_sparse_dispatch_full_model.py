import torch
import json

from backend.scripts.run_aion_int8_sparse_dispatch_full_model import _equivalence, _summarize


def test_equivalence_requires_tokens_and_logits() -> None:
    reference = {"token_ids": [1, 2], "scores": [torch.tensor([1.0]), torch.tensor([2.0])]}
    same = {"token_ids": [1, 2], "scores": [torch.tensor([1.0]), torch.tensor([2.0])]}
    changed = {"token_ids": [1, 3], "scores": [torch.tensor([1.0]), torch.tensor([2.1])]}
    exact = _equivalence(reference, same)
    assert exact["token_ids_exact"]
    assert exact["step_logits_bit_exact"]
    assert exact["maximum_step_logit_error"] == 0
    result = _equivalence(reference, changed)
    assert not result["token_ids_exact"]
    assert not result["step_logits_bit_exact"]


def test_full_model_summary_reports_tail() -> None:
    rows = [{"seconds": value, "time_to_first_token_seconds": value / 2,
             "median_subsequent_token_interval_seconds": value / 4,
             "token_ids": [1] * 64} for value in (1.0, 2.0, 3.0)]
    summary = _summarize(rows)
    assert summary["p50_seconds"] == 2.0
    assert summary["p95_seconds_nearest_rank"] == 3.0


def test_replication_prompt_manifest_is_frozen_and_larger() -> None:
    path = "backend/modules/aion_inference/evals/int8_sparse_dispatch_replication_prompts.v1.json"
    document = json.loads(open(path).read())
    assert document["schema_version"] == "aion.prompt_manifest.v1"
    assert len(document["prompts"]) == 8
    assert len({item["family"] for item in document["prompts"]}) == 8
