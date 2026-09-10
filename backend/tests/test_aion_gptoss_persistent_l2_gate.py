import hashlib

from backend.scripts.run_aion_gptoss_persistent_l2_gate import ORDER, expert_sha


def test_expert_hash_has_fixed_component_order() -> None:
    value = {projection: {kind: f"{projection}-{kind}".encode()
                          for kind in ("weight", "bias")}
             for projection in ("gate", "up", "down")}
    digest = hashlib.sha256()
    for projection, kind in ORDER:
        digest.update(value[projection][kind])
    assert expert_sha(value) == digest.hexdigest()
