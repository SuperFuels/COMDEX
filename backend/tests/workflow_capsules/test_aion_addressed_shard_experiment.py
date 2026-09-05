from __future__ import annotations

import pytest

from backend.modules.aion_inference.shard_selection import AddressedShardExperiment


def test_selected_expert_plan_reads_all_common_and_one_expert_per_layer(tmp_path):
    experiment = AddressedShardExperiment(tmp_path / "shards")
    report = experiment.run(layer_count=3, experts_per_layer=4, selected_per_layer=1, common_bytes=4096, expert_bytes=8192, iterations=2)
    assert report["full"]["shard_count"] == 15
    assert report["selected"]["shard_count"] == 6
    assert report["full"]["all_shards_verified"] is True
    assert report["selected"]["all_shards_verified"] is True
    assert report["measured_byte_reduction_percent"] == pytest.approx(66.6666666667)
    assert report["claim_boundary"]["not_proven"].startswith("model quality")


def test_selection_requires_at_least_one_expert_for_every_layer(tmp_path):
    experiment = AddressedShardExperiment(tmp_path / "shards")
    shards = experiment.build_fixture(layer_count=2, experts_per_layer=2, common_bytes=4096, expert_bytes=4096)
    with pytest.raises(ValueError, match="every layer"):
        experiment.select_experts(shards, {0: ["e0"]})


def test_existing_corrupt_shard_is_refused(tmp_path):
    experiment = AddressedShardExperiment(tmp_path / "shards")
    experiment.build_fixture(layer_count=1, experts_per_layer=2, common_bytes=4096, expert_bytes=4096)
    path = tmp_path / "shards" / "layer-000-common.bin"
    path.write_bytes(b"corrupt")
    with pytest.raises(RuntimeError, match="identity check"):
        experiment.build_fixture(layer_count=1, experts_per_layer=2, common_bytes=4096, expert_bytes=4096)
