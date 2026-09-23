from backend.scripts.run_aion_storage_first_boot import _is_expert_tensor


def test_storage_first_boot_skips_only_combined_expert_tensors() -> None:
    assert _is_expert_tensor(
        "model.layers.0.block_sparse_moe.input_linear.weight"
    )
    assert _is_expert_tensor(
        "model.layers.31.block_sparse_moe.output_linear.weight"
    )
    assert not _is_expert_tensor(
        "model.layers.0.block_sparse_moe.router.layer.weight"
    )
    assert not _is_expert_tensor("model.layers.0.self_attn.q_proj.weight")
    assert not _is_expert_tensor("model.embed_tokens.weight")
