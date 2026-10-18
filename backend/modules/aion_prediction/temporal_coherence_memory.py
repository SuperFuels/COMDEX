"""
Tessaris Temporal Coherence Memory (TCM)
────────────────────────────────────────
Manages sequential context and probabilistic transition memory for the
Predictive Bias Layer (PBL).

Stores symbol triplets, computes Markov probabilities, and logs temporal
accuracy and confidence. Used by PredictiveBias and FusionCore.
"""

import json
import random
import os
import time
import uuid
from collections import deque, defaultdict
from pathlib import Path

from backend.modules.aion_learning.vault_store import AionLearningVaultStore

TEMPORAL_BUFFER_PATH = Path("data/predictive/temporal_buffer.json")
TEMPORAL_MODEL_PATH = Path("data/prediction/temporal_model.json")


class TemporalCoherenceMemory:
    def __init__(
        self,
        window_size: int = 5,
        *,
        vault_store: AionLearningVaultStore | None = None,
        buffer_path: str | Path | None = None,
        model_path: str | Path | None = None,
    ):
        self.window_size = window_size
        explicit_paths = buffer_path is not None or model_path is not None
        self.vault_store = vault_store or AionLearningVaultStore(
            auto_configure=not explicit_paths
        )
        self.buffer_path = Path(buffer_path or TEMPORAL_BUFFER_PATH)
        self.model_path = Path(model_path or TEMPORAL_MODEL_PATH)
        self.sequence_buffer = deque(maxlen=window_size)
        self.temporal_sequences = []
        self.markov_graph = defaultdict(lambda: defaultdict(float))
        self.temporal_accuracy = 0.0
        self.prediction_confidence = 0.5
        self._load_model()

    # ─────────────────────────────────────────────
    # Sequence & triplet management
    # ─────────────────────────────────────────────
    def update_sequence(self, symbol: str):
        self.sequence_buffer.append(symbol)
        if len(self.sequence_buffer) >= 3:
            triplet = tuple(self.sequence_buffer)[-3:]
            self.temporal_sequences.append(triplet)
            self._append_to_buffer_file(triplet)

    def _append_to_buffer_file(self, triplet):
        if self.vault_store.enabled:
            event_id = f"temporal-sequence-{uuid.uuid4()}"
            self.vault_store.append_event(
                event_id,
                {
                    "event_id": event_id,
                    "event_type": "temporal_sequence",
                    "timestamp": time.time(),
                    "triplet": list(triplet),
                },
            )
            return
        self.buffer_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.buffer_path, "a") as f:
            f.write(json.dumps({"triplet": triplet}) + "\n")

    # ─────────────────────────────────────────────
    # Probabilistic next-symbol prediction
    # ─────────────────────────────────────────────
    def update_markov(self, prev_symbol: str, next_symbol: str):
        if not prev_symbol or not next_symbol:
            return
        self.markov_graph[prev_symbol][next_symbol] += 1.0
        self._save_model()

    def predict_next(self):
        if not self.sequence_buffer:
            return None
        last = self.sequence_buffer[-1]
        next_candidates = self.markov_graph.get(last, {})
        if not next_candidates:
            return None
        total = sum(next_candidates.values())
        r = random.random() * total
        for sym, weight in next_candidates.items():
            r -= weight
            if r <= 0:
                return sym
        return None

    def evaluate_prediction(self, predicted, actual):
        score = 1.0 if predicted == actual else 0.0
        self.temporal_accuracy = 0.9 * self.temporal_accuracy + 0.1 * score
        return score

    # ─────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────
    def _load_model(self):
        try:
            if self.vault_store.enabled:
                data = self.vault_store.get_state("temporal_coherence_model", None)
                if data is None:
                    return
            else:
                if not os.path.exists(self.model_path):
                    return
                with open(self.model_path, "r") as f:
                    data = json.load(f)
            for previous, next_counts in data.get("markov_graph", {}).items():
                self.markov_graph[str(previous)].update(
                    {str(symbol): float(count) for symbol, count in next_counts.items()}
                )
            self.prediction_confidence = data.get("confidence", 0.5)
        except Exception as e:
            print(f"[TCM] load failed: {e}")

    def _save_model(self):
        try:
            data = {
                "markov_graph": {
                    str(key): dict(value) for key, value in self.markov_graph.items()
                },
                "confidence": self.prediction_confidence,
            }
            if self.vault_store.enabled:
                self.vault_store.put_state("temporal_coherence_model", data)
            else:
                self.model_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.model_path, "w") as f:
                    json.dump(data, f)
        except Exception as e:
            print(f"[TCM] save failed: {e}")

    # ─────────────────────────────────────────────
    # Reinforcement
    # ─────────────────────────────────────────────
    def reinforce(self, last_symbol: str, actual_symbol: str):
        self.update_markov(last_symbol, actual_symbol)
        self.prediction_confidence = min(1.0, self.prediction_confidence + 0.01)

    def apply_pal_feedback(self, reward: float):
        delta = (reward - 0.5) * 0.05
        self.prediction_confidence = max(0.0, min(1.0, self.prediction_confidence + delta))
