"""AION Phase 21K — Persistent Self-Improvement Memory.

Phase 21I proved in-run improvement. Phase 21K persists the learned strategy so
AION can start future runs with previous corrections instead of relearning from
zero.

This is still operational learning evidence, not a claim of biological
consciousness.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from backend.modules.aion_self_improvement.self_improvement_trial_loop import (
    AionSelfImprovementTrialLoop,
    TrialLoopResult,
)


DEFAULT_MEMORY_PATH = Path("data/aion_self_improvement/persistent_strategy_memory.json")


@dataclass(frozen=True)
class PersistentSelfImprovementMemoryRecord:
    memory_version: str
    task_name: str
    learned_prompt_map: Dict[str, str]
    misses: Dict[str, int]
    best_score: float
    run_count: int
    last_improvement_delta: float
    meta_awareness: float
    response_bias: str
    source_loop_version: str
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PersistentSelfImprovementResult:
    persistence_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    before_known_mapping_count: int
    after_known_mapping_count: int
    baseline_score: float
    final_score: float
    improvement_delta: float
    improved: bool
    equilibrium_reached: bool
    record: Dict[str, Any]
    loop_result: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionPersistentSelfImprovementMemory:
    def __init__(self, memory_path: Optional[Path] = None):
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)

    def load(self) -> Optional[PersistentSelfImprovementMemoryRecord]:
        if not self.memory_path.exists():
            return None
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(data, dict):
            return None

        return PersistentSelfImprovementMemoryRecord(
            memory_version=str(data.get("memory_version", "phase21k_persistent_self_improvement_memory_v1")),
            task_name=str(data.get("task_name", "unknown")),
            learned_prompt_map=dict(data.get("learned_prompt_map", {})),
            misses={str(k): int(v) for k, v in dict(data.get("misses", {})).items()},
            best_score=float(data.get("best_score", 0.0)),
            run_count=int(data.get("run_count", 0)),
            last_improvement_delta=float(data.get("last_improvement_delta", 0.0)),
            meta_awareness=float(data.get("meta_awareness", 0.0)),
            response_bias=str(data.get("response_bias", "unknown")),
            source_loop_version=str(data.get("source_loop_version", "unknown")),
            boundary_statement=str(
                data.get(
                    "boundary_statement",
                    "This is persistent operational self-improvement memory, not biological consciousness.",
                )
            ),
        )

    def save_from_loop_result(self, loop_result: TrialLoopResult) -> PersistentSelfImprovementMemoryRecord:
        previous = self.load()
        final_strategy = loop_result.final_strategy

        previous_map = previous.learned_prompt_map if previous else {}
        learned_prompt_map = dict(previous_map)
        learned_prompt_map.update(dict(final_strategy.get("known_prompt_map", {})))

        previous_misses = previous.misses if previous else {}
        run_misses: Dict[str, int] = {}
        for attempt in loop_result.attempts:
            if not bool(attempt.get("correct", False)):
                prompt = str(attempt.get("prompt", "unknown"))
                run_misses[prompt] = run_misses.get(prompt, 0) + 1

        misses = dict(previous_misses)
        for key, value in run_misses.items():
            misses[str(key)] = int(misses.get(str(key), 0)) + int(value)

        best_score = max(float(previous.best_score) if previous else 0.0, float(loop_result.final_score))
        run_count = int(previous.run_count) + 1 if previous else 1

        meta_state = loop_result.meta_awareness_state or {}
        record = PersistentSelfImprovementMemoryRecord(
            memory_version="phase21k_persistent_self_improvement_memory_v1",
            task_name=loop_result.task_name,
            learned_prompt_map=learned_prompt_map,
            misses=misses,
            best_score=best_score,
            run_count=run_count,
            last_improvement_delta=float(loop_result.improvement_delta),
            meta_awareness=float(meta_state.get("meta_awareness", 0.0)),
            response_bias=str(final_strategy.get("response_bias", meta_state.get("next_response_bias", "unknown"))),
            source_loop_version=loop_result.loop_version,
            boundary_statement=(
                "This persists operational self-improvement corrections across runs. "
                "It does not prove general intelligence or biological consciousness."
            ),
        )

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        return record


def run_persistent_self_improvement(
    *,
    memory_path: Optional[Path] = None,
    max_rounds: int = 8,
    task_name: str = "symbolic_association_self_improvement",
) -> PersistentSelfImprovementResult:
    memory = AionPersistentSelfImprovementMemory(memory_path)
    previous = memory.load()

    loop = AionSelfImprovementTrialLoop(max_rounds=max_rounds)

    if previous is not None:
        loop.strategy["known_prompt_map"] = dict(previous.learned_prompt_map)
        loop.strategy["misses"] = dict(previous.misses)
        loop.strategy["version"] = max(1, int(previous.run_count))
        loop.strategy["mode"] = "persistent_memory_bootstrap"
        loop.strategy["response_bias"] = previous.response_bias

    before_known = len(loop.strategy.get("known_prompt_map", {}))

    loop_result = loop.run(task_name=task_name)
    record = memory.save_from_loop_result(loop_result)

    after_known = len(record.learned_prompt_map)

    evidence = {
        "uses_persistent_memory": True,
        "memory_loaded": previous is not None,
        "uses_llm_shortcut": False,
        "uses_trial_and_error": True,
        "starts_from_previous_strategy": previous is not None,
        "persistent_mapping_count": after_known,
        "run_count": record.run_count,
        "best_score": record.best_score,
    }

    return PersistentSelfImprovementResult(
        persistence_version="phase21k_persistent_self_improvement_memory_v1",
        task_name=task_name,
        memory_loaded=previous is not None,
        memory_path=str(memory.memory_path),
        before_known_mapping_count=before_known,
        after_known_mapping_count=after_known,
        baseline_score=float(loop_result.baseline_score),
        final_score=float(loop_result.final_score),
        improvement_delta=float(loop_result.improvement_delta),
        improved=bool(loop_result.improved),
        equilibrium_reached=bool(loop_result.equilibrium_reached),
        record=record.to_dict(),
        loop_result=loop_result.to_dict(),
        evidence=evidence,
        boundary_statement=(
            "This demonstrates persistent operational self-improvement memory across runs. "
            "It does not prove general intelligence or biological consciousness."
        ),
    )


if __name__ == "__main__":
    result = run_persistent_self_improvement()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\n✅ Persistent self-improvement memory saved to: {result.memory_path}")
