from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from backend.modules.hexcore.latent_causal_state_discovery import (
    GovernedLatentStateLearner,
    HiddenModeLampEnvironment,
    _latent_accuracy,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
)


ACTIONS = ["toggle_mode", "switch_mode", "pulse", "idle"]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "latent_state_benchmark_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _environment_factory(toggle_action: str):
    def factory(_episode_index: int):
        return HiddenModeLampEnvironment(
            toggle_action=toggle_action,
            initial_lamp=0,
            initial_mode=0,
        ).step

    return factory


def run_latent_state_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    learner = GovernedLatentStateLearner(runtime.store)
    sequences = learner.design_diagnostic_sequences(
        actions=ACTIONS,
        episode_count=40,
        steps_per_episode=12,
    )

    phase_a_rows = learner.collect(
        experiment_runner_factory=_environment_factory("toggle_mode"),
        sequences=sequences,
        phase="phase_a",
    )
    phase_a = learner.discover_or_revise(
        world_id="hidden_mode_lamp_v1",
        visible_variables=["lamp"],
        actions=ACTIONS,
        rows=phase_a_rows,
        adequacy_gate=0.98,
        minimum_held_out_gain=0.05,
        persist=True,
    )
    first_graph = dict(
        runtime.store.state["causal_graphs"]["hidden_mode_lamp_v1"]
    )

    # The environment changes: the old hidden-mode transition action is no
    # longer causal. A fresh, source-held-out set must force graph revision.
    phase_b_rows = learner.collect(
        experiment_runner_factory=_environment_factory("switch_mode"),
        sequences=list(reversed(sequences)),
        phase="phase_b",
    )
    phase_b = learner.discover_or_revise(
        world_id="hidden_mode_lamp_v1",
        visible_variables=["lamp"],
        actions=ACTIONS,
        rows=phase_b_rows,
        adequacy_gate=0.98,
        minimum_held_out_gain=0.05,
        persist=True,
    )
    second_graph = dict(
        runtime.store.state["causal_graphs"]["hidden_mode_lamp_v1"]
    )

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained_record = restarted.store.state["causal_graphs"].get(
        "hidden_mode_lamp_v1"
    )
    retained_graph = learner.graph_from_record(retained_record)
    _, phase_b_held_out = learner.split_by_episode(phase_b_rows)
    restart_accuracy = _latent_accuracy(
        retained_graph, phase_b_held_out
    )
    latent_records = restarted.store.state["latent_variables"]
    active_latents = [
        row for row in latent_records.values()
        if row.get("status") == "active"
    ]
    superseded_latents = [
        row for row in latent_records.values()
        if row.get("status") == "superseded"
    ]

    result = {
        "schema_version": "aion.hexcore.latent_state_benchmark.v1",
        "benchmark": "hidden_state_construction_and_revision",
        "language_provider_used": False,
        "hidden_state_labels_supplied": False,
        "latent_candidate_graphs_supplied": False,
        "visible_variables_supplied": ["lamp"],
        "actions_supplied": ACTIONS,
        "diagnostic_sequences_selected_by_learner": True,
        "phase_a": phase_a,
        "phase_b_change": phase_b,
        "graphs": {
            "phase_a": first_graph,
            "phase_b": second_graph,
        },
        "restart": {
            "retained_graph_id": retained_record.get("graph_id"),
            "retained_revision": retained_record.get("revision"),
            "phase_b_held_out_accuracy": round(
                restart_accuracy, 8
            ),
            "active_latent_variables": len(active_latents),
            "superseded_latent_variables": len(
                superseded_latents
            ),
            "relearning_experiments": 0,
        },
        "gates": {
            "visible_model_rejected_phase_a": (
                phase_a["model_criticism"]["decision"]
                == "NONE_ADEQUATE"
            ),
            "latent_state_constructed": phase_a["accepted"],
            "phase_a_held_out_accuracy_at_least_90_percent": (
                phase_a["held_out_accuracy"] >= 0.90
            ),
            "retained_latent_model_rejected_after_change": (
                phase_b["model_criticism"]["decision"]
                == "NONE_ADEQUATE"
            ),
            "latent_dynamics_revised": (
                phase_b["accepted"]
                and first_graph["latent_toggle_action"]
                != second_graph["latent_toggle_action"]
                and second_graph["supersedes_graph_id"]
                == first_graph["graph_id"]
            ),
            "phase_b_held_out_accuracy_at_least_90_percent": (
                phase_b["held_out_accuracy"] >= 0.90
            ),
            "complexity_bounded": (
                phase_a["proposed_graph"]["complexity"] <= 6
                and phase_b["proposed_graph"]["complexity"] <= 6
            ),
            "restart_retention_without_relearning": (
                restart_accuracy >= 0.90
                and retained_record.get("revision") == 2
                and len(active_latents) == 1
                and len(superseded_latents) == 1
            ),
        },
        "boundary_statement": (
            "This demonstrates construction and revision of one bounded binary "
            "latent state in a controlled partially observable process. It does "
            "not demonstrate arbitrary latent-variable discovery."
        ),
    }
    result["passed"] = all(result["gates"].values())
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/hexcore/latent_state_learning.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_latent_state_benchmark.json"),
    )
    args = parser.parse_args()
    result = run_latent_state_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
