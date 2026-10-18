from __future__ import annotations

from backend.modules.aion_inference.baseline import (
    StreamGeneration,
    WorkloadCase,
    benchmark_storage,
    collect_model_store_evidence,
    load_workloads,
    run_baseline,
)


class FakeClient:
    def generate(self, *, model: str, case: WorkloadCase) -> StreamGeneration:
        assert model == "test-model"
        return StreamGeneration(
            text="723",
            first_token_seconds=0.125,
            wall_seconds=0.5,
            final_event={
                "model": model,
                "done": True,
                "done_reason": "stop",
                "load_duration": 10_000_000,
                "prompt_eval_count": 12,
                "prompt_eval_duration": 100_000_000,
                "eval_count": 3,
                "eval_duration": 300_000_000,
            },
        )


def test_workload_manifest_covers_locked_plan_categories():
    categories = {case.category for case in load_workloads()}
    assert categories == {
        "simple_arithmetic",
        "structured_business_calculation",
        "classification",
        "document_interpretation",
        "planning",
        "tool_selection",
        "novel_reasoning",
        "long_context",
        "repeated_task_variation",
    }


def test_baseline_measures_supported_values_and_marks_unknowns_unavailable():
    case = WorkloadCase(
        case_id="arithmetic-test",
        category="simple_arithmetic",
        prompt="437 + 286",
        quality_check={"type": "regex", "pattern": r"^723$"},
    )
    report = run_baseline(
        model="test-model", cases=[case], client=FakeClient(), machine={"machine": "fixture"}
    )
    result = report.results[0]

    assert report.schema_version == "aion.inference.baseline.v1"
    assert result.quality_status == "pass"
    assert result.measurements["time_to_first_token"].value == 0.125
    assert result.measurements["prompt_tokens"].value == 12
    assert result.measurements["tokens_per_second"].value == 10.0
    assert result.measurements["peak_unified_memory"].status == "unavailable"
    assert result.measurements["ssd_bytes_read"].value is None
    assert result.measurements["energy"].note
    assert len(result.response_sha256) == 64
    assert report.run_id.startswith("baseline-")


def test_baseline_run_identity_is_stable_for_same_inputs_and_response():
    case = WorkloadCase(
        case_id="stable",
        category="simple_arithmetic",
        prompt="437 + 286",
        quality_check={"type": "contains_all", "values": ["723"]},
    )
    first = run_baseline(model="test-model", cases=[case], client=FakeClient(), machine={})
    second = run_baseline(model="test-model", cases=[case], client=FakeClient(), machine={})
    assert first.run_id == second.run_id
    assert first.results[0].response_sha256 == second.results[0].response_sha256


def test_storage_probe_is_bounded_verified_and_removes_temporary_file(tmp_path):
    evidence = benchmark_storage(tmp_path, probe_bytes=1024 * 1024)
    assert evidence["status"] == "measured"
    assert evidence["probe_bytes"] == 1024 * 1024
    assert evidence["read_mib_per_second"] > 0
    assert evidence["write_mib_per_second"] > 0
    assert len(evidence["content_sha256"]) == 64
    assert list(tmp_path.iterdir()) == []


def test_model_store_evidence_hashes_manifest(tmp_path):
    manifest = tmp_path / "manifests/registry.ollama.ai/library/qwen3/1.7b"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"layers":[{"size":12},{"size":30}]}', encoding="utf-8")
    evidence = collect_model_store_evidence(tmp_path, "qwen3:1.7b")
    assert evidence["manifest_available"] is True
    assert evidence["declared_layer_bytes"] == 42
    assert evidence["declared_layer_count"] == 2
    assert len(evidence["manifest_sha256"]) == 64
