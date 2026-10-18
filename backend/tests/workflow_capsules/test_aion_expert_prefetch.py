from __future__ import annotations

import hashlib
import json

import pytest

from backend.modules.aion_inference import (
    broad_expert_prefetch_plan,
    build_expert_working_set_dictionary,
    build_cross_layer_route_capsule,
    build_expert_prefetch_plan,
    collapse_beams_cost_aware,
    ExpertRouteCorpus,
    optimize_expert_cache_budget,
    optimize_expert_cache_memory_budget,
    predict_cross_layer_experts,
    simulate_frequency_cache_demand_bytes,
    select_predictive_retention,
    verify_promoted_expert_cache_plan,
    verify_cross_layer_route_capsule,
    verify_expert_working_set_dictionary,
    SQICandidateBeam,
)
from backend.scripts.run_aion_layer_scoped_moe_experiment import (
    LayerScopedStore,
    select_frequency_retention,
)
from backend.scripts.run_aion_storage_first_multiprompt import (
    _first_token_mismatch,
    _select_prompts,
    _step_error_summary,
    _valid_generation_termination,
    _validate_prompt_catalog,
)
from backend.scripts.run_aion_promoted_cache_plan_replication import CASES, _comparison_cases
from backend.scripts import run_aion_moe_latency_attribution as latency_attribution
from backend.scripts.run_aion_moe_latency_attribution import (
    _verify_storage_device,
    summarize_stage_seconds,
)
from backend.scripts.run_aion_metal_transfer_abba import _p95
from backend.scripts.aion_lossless_codec_probe import (
    _lz4_compress,
    _lz4_decode,
    _lz4_library,
    _shuffle2,
)


def _routing_profile():
    return {
        "architecture": {"experts_per_layer": 4, "experts_selected_per_token": 2},
        "method": {"coverage_target": 0.95},
        "training": {
            "counts_by_domain": {
                "arithmetic": [[8, 2, 0, 0], [0, 1, 8, 1]],
                "business": [[6, 4, 0, 0], [0, 2, 7, 1]],
                "policy": [[0, 1, 8, 1], [7, 0, 1, 2]],
                "coding": [[1, 0, 2, 7], [1, 7, 2, 0]],
                "general": [[2, 6, 1, 1], [2, 1, 1, 6]],
            },
            "resident_experts_by_layer": [[0, 1, 2], [0, 1, 2, 3]],
        },
    }


def _route_observation(digest: str, routes):
    return {
        "architecture": {"layers": 2, "experts_per_layer": 4},
        "bindings": {"model": "a" * 64},
        "observation_sha256": digest,
        "route_batches_by_layer": routes,
    }


def test_cross_layer_route_capsule_is_bounded_hash_bound_and_resident_aware():
    observations = [
        _route_observation(
            "1" * 64,
            [
                [[(0, 1)], [(0, 2)]],
                [[(2, 3)], [(2, 3)]],
            ],
        ),
        _route_observation(
            "2" * 64,
            [
                [[(0, 1)], [(1, 2)]],
                [[(2, 3)], [(1, 2)]],
            ],
        ),
    ]
    capsule = build_cross_layer_route_capsule(
        observations, confidence_threshold=0.75, max_predictions_per_layer=1
    )
    verify_cross_layer_route_capsule(capsule, expected_bindings={"model": "a" * 64})
    predicted = predict_cross_layer_experts(
        capsule, target_layer=1, source_route=(0, 1), resident_experts=(2,)
    )
    assert len(predicted) == 1
    assert predicted[0]["expert"] == 3
    assert predicted[0]["confidence"] == 1.0
    assert predict_cross_layer_experts(
        capsule, target_layer=1, source_route=(0,), resident_experts=(2, 3)
    ) == ()

    tampered = json.loads(json.dumps(capsule))
    tampered["method"]["confidence_threshold"] = 0.5
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_cross_layer_route_capsule(tampered)


def test_gateway_profile_builds_deterministic_bounded_layer_plan():
    profile = _routing_profile()
    first = build_expert_prefetch_plan(profile, "arithmetic_business", coverage_target=0.80)
    second = build_expert_prefetch_plan(profile, "arithmetic_business", coverage_target=0.80)
    assert first.experts_by_layer == ((0, 1), (1, 2))
    assert first.expert_count_by_layer == (2, 2)
    assert first.plan_sha256 == second.plan_sha256
    assert first.source_domains == ("arithmetic", "business")


def test_broad_plan_reuses_measured_cross_domain_resident_sets():
    plan = broad_expert_prefetch_plan(_routing_profile())
    assert plan.profile == "broad_control"
    assert plan.experts_by_layer == ((0, 1, 2), (0, 1, 2, 3))
    assert plan.coverage_target == 0.95


def test_layer_ahead_plan_can_be_capped_at_native_router_top_k():
    plan = build_expert_prefetch_plan(
        _routing_profile(), "policy", coverage_target=0.99, max_experts_per_layer=2
    )
    assert plan.max_experts_per_layer == 2
    assert plan.expert_count_by_layer == (2, 2)


def test_prefetch_plan_rejects_unknown_profile_and_invalid_coverage():
    with pytest.raises(ValueError, match="unsupported"):
        build_expert_prefetch_plan(_routing_profile(), "imaginary")
    with pytest.raises(ValueError, match="coverage_target"):
        build_expert_prefetch_plan(_routing_profile(), "policy", coverage_target=0.0)
    with pytest.raises(ValueError, match="max_experts_per_layer"):
        build_expert_prefetch_plan(_routing_profile(), "policy", max_experts_per_layer=1)


def test_layer_store_retains_bounded_union_of_two_live_routes():
    store = LayerScopedStore(0, {"experts": []})
    store.active = {1: ("i1", "o1"), 2: ("i2", "o2"), 3: ("i3", "o3")}
    store.release_with_lru_routes(((1, 2),), 2)
    assert set(store.retained) == {1, 2}

    store.active = {2: ("i2-new", "o2-new"), 3: ("i3", "o3")}
    store.release_with_lru_routes(((2, 3),), 2)
    assert set(store.retained) == {1, 2, 3}

    store.active = {3: ("i3-new", "o3-new")}
    store.release_with_lru_routes(((3,),), 2)
    assert set(store.retained) == {2, 3}


def test_layer_store_frequency_cache_is_bounded_and_rewards_reuse():
    store = LayerScopedStore(0, {"experts": []})
    store.active = {expert: (f"i{expert}", f"o{expert}") for expert in (1, 2, 3)}
    store.release_with_frequency_capacity(((1, 2), (1, 3)), 2)
    assert set(store.retained) == {1, 3}

    store.active = {2: ("i2-new", "o2-new")}
    store.release_with_frequency_capacity(((2,), (2,)), 2)
    assert set(store.retained) == {1, 2}
    assert len(store.retained) == 2


def test_layer_store_frequency_cache_rejects_zero_capacity():
    store = LayerScopedStore(0, {"experts": []})
    with pytest.raises(ValueError, match="capacity"):
        store.release_with_frequency_capacity(((1,),), 0)


def test_pre_activation_frequency_selection_matches_post_activation_policy():
    routes = ((1, 2), (1, 3))
    counts: dict[int, int] = {}
    recency: dict[int, int] = {}
    selected, clock = select_frequency_retention(
        routes, {1, 2, 3}, counts, recency, 0, 2
    )
    assert selected == (1, 3)
    assert clock == 2

    store = LayerScopedStore(0, {"experts": []})
    store.active = {expert: (f"i{expert}", f"o{expert}") for expert in (1, 2, 3)}
    store.release_with_frequency_capacity(routes, 2)
    assert tuple(store.retained) == selected
    assert store.usage_counts == counts
    assert store.last_used == recency


def test_frequency_selection_rejects_zero_capacity():
    with pytest.raises(ValueError, match="capacity"):
        select_frequency_retention(((1,),), {1}, {}, {}, 0, 0)


def test_working_set_dictionary_protects_only_available_predicted_experts():
    observations = [
        _route_observation(
            "1" * 64,
            [
                [[(0, 1)], [(1, 2)], [(0, 1)]],
                [[(2, 3)], [(2, 3)]],
            ],
        )
    ]
    dictionary = build_expert_working_set_dictionary(observations)
    verify_expert_working_set_dictionary(
        dictionary, expected_bindings={"model": "a" * 64}
    )
    selected, clock = select_predictive_retention(
        routes=((0, 1),),
        available_experts={0, 1, 2},
        usage_counts={},
        last_used={},
        usage_clock=0,
        capacity=2,
        layer_dictionary=dictionary["layers"][0],
    )
    assert selected == (1, 2)
    assert clock == 1
    assert set(selected) <= {0, 1, 2}


def test_working_set_dictionary_is_hash_and_binding_bound():
    dictionary = build_expert_working_set_dictionary([
        _route_observation("2" * 64, [[[(0, 1)], [(1, 2)]], [[(2, 3)], [(2, 3)]]])
    ])
    tampered = json.loads(json.dumps(dictionary))
    tampered["layers"][0]["next_expert_prior"]["2"] = 999
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_expert_working_set_dictionary(tampered)
    with pytest.raises(ValueError, match="binding mismatch"):
        verify_expert_working_set_dictionary(
            dictionary, expected_bindings={"model": "b" * 64}
        )


def test_cost_aware_collapse_fuses_exact_execution_signatures_and_avoids_model():
    beams = (
        SQICandidateBeam(
            "calculation_a", "verified_atomsheet", 1.0, True, "verified",
            {"execution_signature": "sheet:tax-v1", "execution_cost": {"model_calls": 0, "estimated_storage_bytes": 0, "estimated_ttft_ms": 1}},
        ),
        SQICandidateBeam(
            "calculation_b", "verified_atomsheet", 0.99, True, "same_contract",
            {"execution_signature": "sheet:tax-v1", "execution_cost": {"model_calls": 0, "estimated_storage_bytes": 0, "estimated_ttft_ms": 1}},
        ),
        SQICandidateBeam(
            "model", "full_model", 0.55, True, "fallback",
            {"execution_signature": "model:granite", "execution_cost": {"model_calls": 1, "estimated_storage_bytes": 10_000, "estimated_ttft_ms": 1000}},
        ),
    )
    collapse, fusion = collapse_beams_cost_aware(beams)
    assert collapse.selected_beam_id == "calculation_a"
    assert collapse.selected_route == "verified_atomsheet"
    fused = next(item for item in fusion if item["execution_signature"] == "sheet:tax-v1")
    assert fused["fused_beam_ids"] == ("calculation_a", "calculation_b")
    assert fused["fused_count"] == 2


def test_step_error_summary_localizes_first_and_maximum_divergence():
    summary = _step_error_summary([0.0, 0.015625, 0.0, 0.03125], [10, 11, 12, 13])
    assert summary["nonzero_step_logit_error_count"] == 2
    assert summary["first_nonzero_step_logit_error"] == {
        "step_index": 1,
        "maximum_absolute_error": 0.015625,
        "selected_token_id": 11,
    }
    assert summary["maximum_step_logit_error_index"] == 3
    assert summary["nonzero_step_logit_errors"][-1]["selected_token_id"] == 13
    exact = _step_error_summary([0.0, 0.0], [10, 11])
    assert exact["maximum_step_logit_error_index"] is None


def test_first_token_mismatch_records_value_and_length_divergence():
    assert _first_token_mismatch([1, 2, 4], [1, 2, 3]) == 2
    assert _first_token_mismatch([1, 2, 3], [1, 2]) == 2
    assert _first_token_mismatch([1, 2], [1, 2]) is None


def test_generation_termination_accepts_limit_or_exact_eos_only():
    assert _valid_generation_termination([1, 2, 3], 3, 0)
    assert _valid_generation_termination([1, 0], 3, 0)
    assert not _valid_generation_termination([1, 2], 3, 0)
    assert not _valid_generation_termination([], 3, 0)


def test_storage_first_prompt_selection_supports_bounded_diagnostics():
    selected = _select_prompts(["commercial_risk", "commercial_risk"], 20260906)
    assert [item["family"] for item in selected] == ["commercial_risk"]
    with pytest.raises(ValueError, match="unknown prompt families"):
        _select_prompts(["does_not_exist"], 20260906)


def test_storage_first_prompt_manifest_is_bounded_and_rejects_duplicates():
    catalog = _validate_prompt_catalog({
        "schema_version": "aion.prompt_manifest.v1",
        "prompts": [
            {"family": "task_a", "prompt": "Perform task A."},
            {"family": "task_b", "prompt": "Perform task B."},
        ],
    })
    selected = _select_prompts(["task_b"], 7, catalog)
    assert selected == [{"family": "task_b", "prompt": "Perform task B."}]
    with pytest.raises(ValueError, match="duplicate prompt family"):
        _validate_prompt_catalog({
            "schema_version": "aion.prompt_manifest.v1",
            "prompts": [
                {"family": "task_a", "prompt": "One."},
                {"family": "task_a", "prompt": "Two."},
            ],
        })


def test_frequency_cache_simulator_matches_expected_fault_bytes():
    entries = {0: {"bytes": 10}, 1: {"bytes": 10}}
    batches = (((0,),), ((1,),), ((0,),), ((1,),))
    assert simulate_frequency_cache_demand_bytes(batches, entries, 0) == 40
    assert simulate_frequency_cache_demand_bytes(batches, entries, 1) == 40
    assert simulate_frequency_cache_demand_bytes(batches, entries, 2) == 20


def test_budget_optimizer_moves_slots_to_the_layer_with_marginal_reuse():
    entries = ({0: {"bytes": 10}, 1: {"bytes": 10}}, {0: {"bytes": 10}, 1: {"bytes": 10}})
    routes = (
        (((0,),), ((1,),), ((0,),), ((1,),)),
        (),
    )
    plan = optimize_expert_cache_budget(routes, entries, total_capacity=2)
    assert plan.capacities_by_layer == (2, 0)
    assert plan.predicted_demand_bytes == 20
    assert plan.uniform_predicted_demand_bytes == 40
    assert plan.predicted_byte_reduction_percent == 50.0
    assert len(plan.plan_sha256) == 64


def test_memory_budget_optimizer_respects_bytes_and_moves_capacity_to_reuse():
    entries = (
        {0: {"bytes": 10}, 1: {"bytes": 10}},
        {0: {"bytes": 20}, 1: {"bytes": 20}},
    )
    routes = (
        (((0,),), ((1,),), ((0,),), ((1,),)),
        (((0,),),),
    )
    plan = optimize_expert_cache_memory_budget(
        routes, entries, maximum_resident_bytes=20
    )
    assert plan.capacities_by_layer == (2, 0)
    assert plan.estimated_resident_bytes == 20
    assert plan.estimated_resident_bytes <= plan.maximum_resident_bytes
    assert plan.predicted_demand_bytes == 40
    assert plan.uniform_capacity == 0
    assert len(plan.plan_sha256) == 64


def test_memory_budget_optimizer_is_conservative_for_unequal_experts():
    entries = ({0: {"bytes": 9}, 1: {"bytes": 11}},)
    routes = ((((0,),), ((0,),), ((1,),)),)
    plan = optimize_expert_cache_memory_budget(
        routes, entries, maximum_resident_bytes=20
    )
    assert plan.capacities_by_layer == (1,)
    assert plan.estimated_resident_bytes == 11
    assert plan.estimated_resident_bytes <= 20


def test_memory_budget_optimizer_rejects_invalid_budget_and_empty_layer():
    with pytest.raises(ValueError, match="non-negative"):
        optimize_expert_cache_memory_budget(
            ((),), ({0: {"bytes": 1}},), maximum_resident_bytes=-1
        )
    with pytest.raises(ValueError, match="every layer"):
        optimize_expert_cache_memory_budget(((),), ({},), maximum_resident_bytes=1)


def test_latency_attribution_reports_percentages_and_unassigned_time():
    summary = summarize_stage_seconds({"storage": 3.0, "compute": 2.0}, 10.0)
    assert summary["attributed_percent"] == 50.0
    assert summary["unassigned_seconds"] == 5.0
    assert summary["stage_percent_of_total"] == {"storage": 30.0, "compute": 20.0}
    with pytest.raises(ValueError, match="positive"):
        summarize_stage_seconds({"storage": 1.0}, 0.0)
    with pytest.raises(ValueError, match="non-negative"):
        summarize_stage_seconds({"storage": -1.0}, 1.0)


def test_physical_disk_evidence_is_bound_to_storage_mount(monkeypatch):
    class Result:
        stdout = "Filesystem 512-blocks Used Available Capacity Mounted on\n/dev/disk6s2 1 1 1 1% /Volumes/card\n"

    monkeypatch.setattr(latency_attribution.subprocess, "run", lambda *args, **kwargs: Result())
    assert _verify_storage_device(latency_attribution.Path("/Volumes/card"), "disk6") == "disk6"
    with pytest.raises(RuntimeError, match="does not belong"):
        _verify_storage_device(latency_attribution.Path("/Volumes/card"), "disk4")


def test_lz4_bf16_shuffle_roundtrip_is_byte_exact():
    raw = bytes(range(256)) * 64
    compressed = _lz4_compress(_lz4_library(), _shuffle2(raw))
    assert _lz4_decode(_lz4_library(), compressed, len(raw)) == raw


def test_metal_transfer_abba_uses_conservative_small_sample_p95():
    assert _p95([3.0, 5.0]) == 5.0
    with pytest.raises(ValueError, match="observations"):
        _p95([])


def test_promoted_cache_plan_verifier_binds_capacity_and_model():
    document = {
        "schema_version": "aion.promoted_expert_cache_plan.v1",
        "architecture": {"layers": 2, "experts_per_layer": 2},
        "total_capacity": 2,
        "capacities_by_layer": [2, 0],
        "bindings": {
            "model_config_sha256": "a" * 64,
            "shard_manifest_sha256": "b" * 64,
            "pack_manifest_sha256": "c" * 64,
        },
        "integrity": {"promotion_gates_passed": True},
    }
    document["artifact_sha256"] = hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert verify_promoted_expert_cache_plan(
        document,
        expected_model_config_sha256="a" * 64,
        expected_shard_manifest_sha256="b" * 64,
        expected_pack_manifest_sha256="c" * 64,
    ) == (2, 0)
    with pytest.raises(ValueError, match="model_config_sha256"):
        verify_promoted_expert_cache_plan(document, expected_model_config_sha256="d" * 64)


def test_promoted_cache_plan_verifier_rejects_mutation():
    document = {
        "schema_version": "aion.promoted_expert_cache_plan.v1",
        "architecture": {"layers": 1, "experts_per_layer": 2},
        "total_capacity": 1,
        "capacities_by_layer": [1],
        "bindings": {},
        "integrity": {"promotion_gates_passed": True},
    }
    document["artifact_sha256"] = hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    document["capacities_by_layer"] = [2]
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_promoted_expert_cache_plan(document)


def test_route_corpus_is_content_addressed_and_prompt_private(tmp_path):
    corpus = ExpertRouteCorpus(tmp_path / "routes")
    kwargs = {
        "route_batches_by_layer": ((((0, 1),),), (((1,),),)),
        "glyph_address": "glyph:sha256:" + "1" * 64,
        "model_input_sha256": "2" * 64,
        "generated_tokens": 2,
        "model_config_sha256": "3" * 64,
        "shard_manifest_sha256": "4" * 64,
        "pack_manifest_sha256": "5" * 64,
        "experts_per_layer": 2,
    }
    first = corpus.record(**kwargs)
    second = corpus.record(**kwargs)
    assert first == second
    observation = corpus.load(first)
    assert observation["privacy"] == {"prompt_text_stored": False, "model_output_stored": False}
    assert "prompt" not in observation


def test_route_corpus_builds_one_budget_across_multiple_observations(tmp_path):
    corpus = ExpertRouteCorpus(tmp_path / "routes")
    base = {
        "glyph_address": "glyph:sha256:" + "1" * 64,
        "generated_tokens": 2,
        "model_config_sha256": "3" * 64,
        "shard_manifest_sha256": "4" * 64,
        "pack_manifest_sha256": "5" * 64,
        "experts_per_layer": 2,
    }
    digests = [
        corpus.record(
            **base, model_input_sha256=str(number) * 64,
            route_batches_by_layer=(( ((0,),), ((1,),) ), (((0,),),)),
        )
        for number in (6, 7)
    ]
    entries = ({0: {"bytes": 10}, 1: {"bytes": 10}}, {0: {"bytes": 10}, 1: {"bytes": 10}})
    plan = corpus.optimize(digests, entries, total_capacity=2)
    assert plan.capacities_by_layer == (2, 0)
    assert plan.total_capacity == 2

    memory_plan = corpus.optimize_memory(
        digests, entries, maximum_resident_bytes=20
    )
    assert memory_plan.capacities_by_layer == (2, 0)
    assert memory_plan.estimated_resident_bytes == 20


def test_route_corpus_rejects_an_observation_with_an_empty_layer(tmp_path):
    corpus = ExpertRouteCorpus(tmp_path / "routes")
    with pytest.raises(ValueError, match="every layer"):
        corpus.record(
            route_batches_by_layer=(( ((0,),), ), ()),
            glyph_address="glyph:sha256:" + "1" * 64,
            model_input_sha256="2" * 64,
            generated_tokens=1,
            model_config_sha256="3" * 64,
            shard_manifest_sha256="4" * 64,
            pack_manifest_sha256="5" * 64,
            experts_per_layer=1,
        )


def test_direct_plan_comparison_uses_balanced_longer_unseen_cases():
    first, second, cases = _comparison_cases(direct_comparison=True, longer_corpus=True)
    assert (first, second) == ("reference_512", "candidate_512")
    assert len(cases) == 4
    assert all(case["generated_tokens"] == 24 for case in cases)
    assert [case["order"] for case in cases] == [
        (first, second), (second, first), (first, second), (second, first)
    ]
    legacy_first, legacy_second, legacy_cases = _comparison_cases(
        direct_comparison=False, longer_corpus=False
    )
    assert (legacy_first, legacy_second) == ("uniform_16", "promoted_512")
    assert legacy_cases == CASES
