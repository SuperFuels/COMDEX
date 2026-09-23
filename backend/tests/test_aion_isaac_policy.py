from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import gymnasium as gym
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "aion_isaac_policy", ROOT / "integrations/isaac_lab/aion_isaac_policy.py"
)
assert SPEC and SPEC.loader
POLICY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = POLICY
SPEC.loader.exec_module(POLICY)


ANCESTRY = [{"procedure_id": procedure} for procedure in POLICY.REQUIRED_ANCESTRY]
SPACE = gym.spaces.Box(low=-1.0, high=1.0, shape=(1, 8), dtype=np.float32)


def observation(episode: int, step: int, value: int = 0):
    return {"rgb": np.full((80, 80, 3), value, dtype=np.uint8), "timestamp": step,
            "episode_id": episode, "observation_sha256": "a" * 64,
            "proprioception_bounded": np.zeros(18, dtype=np.float32)}


def test_retained_policy_is_bounded_temporal_and_resets_per_episode() -> None:
    first = POLICY.propose(permitted=observation(0, 0), action_space=SPACE,
                           skill_ancestry=ANCESTRY, arm_id="aion_retained")
    second = POLICY.propose(permitted=observation(0, 1, 255), action_space=SPACE,
                            skill_ancestry=ANCESTRY, arm_id="aion_retained")
    reset = POLICY.propose(permitted=observation(1, 0), action_space=SPACE,
                           skill_ancestry=ANCESTRY, arm_id="aion_retained")
    assert SPACE.contains(first["values"])
    assert SPACE.contains(second["values"])
    assert np.max(np.abs(first["values"])) <= .18
    assert second["prediction"]["identified_channels"] == [0]
    assert reset["prediction"]["identified_channels"] == []
    assert first["action_space_digest"] == POLICY.action_space_digest(SPACE)


def test_cold_arm_has_no_retained_state_and_cosmos_fails_to_claim_use() -> None:
    cold = POLICY.propose(permitted=observation(0, 3), action_space=SPACE,
                          skill_ancestry=[], arm_id="aion_cold")
    cosmos = POLICY.propose(permitted=observation(0, 0), action_space=SPACE,
                            skill_ancestry=ANCESTRY, arm_id="aion_cosmos")
    assert cold["prediction"]["kind"] == "cold_memory_free_probe"
    assert cosmos["prediction"]["cosmos_used"] is False


def test_missing_models_and_tampered_ancestry_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="ancestry"):
        POLICY.propose(permitted=observation(0, 0), action_space=SPACE,
                       skill_ancestry=[], arm_id="aion_retained")
    with pytest.raises(RuntimeError, match="not_attested"):
        POLICY.propose(permitted=observation(0, 0), action_space=SPACE,
                       skill_ancestry=[], arm_id="gr00t_teacher")
