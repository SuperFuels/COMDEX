#!/usr/bin/env python3
"""
AION Phase 31 - Predictive Bias Layer (Unified)
───────────────────────────────────────────────
Learns short-term temporal transitions between perceptual events.
Builds a Markov-style temporal model predicting next glyph or concept.
Integrates with PAL and resonance feedback to reinforce accurate
anticipation. Functions as Aion's temporal coherence engine.

Inputs:
  - data/analysis/pal_events.jsonl
Outputs:
  - data/predictive/predictive_bias_state.json
  - data/predictive/predictive_transitions.jsonl
  - data/prediction/temporal_model.json
"""

import os, json, math, random, time, uuid
from pathlib import Path
from collections import deque, defaultdict, Counter
from typing import Dict, List, Tuple
from itertools import islice
# ─────────────────────────────────────────────
# Temporal Coherence Memory Integration
# ─────────────────────────────────────────────

from backend.modules.aion_prediction.temporal_coherence_memory import TemporalCoherenceMemory
from backend.modules.aion_learning.vault_store import AionLearningVaultStore
# ─────────────────────────────────────────────
# Setup directories
# ─────────────────────────────────────────────
DATA_DIR = Path("data")
ANALYSIS_DIR = DATA_DIR / "analysis"
PRED_DIR = DATA_DIR / "prediction"
PB_DIR = DATA_DIR / "predictive"

EVENTS_PATH = ANALYSIS_DIR / "pal_events.jsonl"
MODEL_PATH = PRED_DIR / "temporal_model.json"
STATE_PATH = PB_DIR / "predictive_bias_state.json"
LOG_PATH = PB_DIR / "predictive_transitions.jsonl"

# ─────────────────────────────────────────────
# Predictive Bias Core
# ─────────────────────────────────────────────
class PredictiveBias:
    def __init__(
        self,
        window_size: int = 5,
        *,
        vault_store: AionLearningVaultStore | None = None,
        events_path: str | Path | None = None,
        model_path: str | Path | None = None,
        state_path: str | Path | None = None,
        log_path: str | Path | None = None,
    ):
        self.window_size = window_size
        explicit_paths = any(
            path is not None
            for path in (events_path, model_path, state_path, log_path)
        )
        self.vault_store = vault_store or AionLearningVaultStore(
            auto_configure=not explicit_paths
        )
        self.events_path = Path(events_path or EVENTS_PATH)
        self.model_path = Path(model_path or MODEL_PATH)
        self.state_path = Path(state_path or STATE_PATH)
        self.log_path = Path(log_path or LOG_PATH)
        self.sequence_buffer = deque(maxlen=window_size)
        self.transitions: Dict[Tuple[str, str], float] = defaultdict(float)
        self.counts: Dict[Tuple[str, str], int] = defaultdict(int)   # 👈 ADD THIS LINE
        self.markov_graph = defaultdict(Counter)
        self.prediction_confidence: float = 0.0
        self.last_prediction: str = None
        self.last_symbol: str = None
        self.tcm = TemporalCoherenceMemory(
            window_size=window_size,
            vault_store=self.vault_store,
            model_path=self.model_path,
        )

    def _append_prediction_event(self, event_type: str, payload: dict) -> None:
        row = dict(payload)
        row.setdefault("timestamp", time.time())
        row["event_type"] = event_type
        if self.vault_store.enabled:
            event_id = f"{event_type}-{uuid.uuid4()}"
            row["event_id"] = event_id
            self.vault_store.append_event(event_id, row)
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(row) + "\n")

    # ─────────────────────────────────────────────
    # Observe event stream (Markov learning)
    # ─────────────────────────────────────────────
    def observe(self, symbol: str):
        """Record symbol transition for Markov-style model."""
        if self.last_symbol is not None:
            self.markov_graph[self.last_symbol][symbol] += 1
        self.last_symbol = symbol

    from itertools import islice

    def train_from_events(self, path=None, keep_last=10000):
        """Train transition graph from PAL event log (adaptive streaming; keeps only last N events)."""
        path = Path(path or self.events_path)
        if not path.exists():
            print(f"⚠️ No PAL events found at {path}")
            return

        valid_syms = {"■","▲","●","◆","⬟","⬢","Ω","λ","ψ","Φ","Δ","Σ"}
        event_count = 0

        # ─────────────────────────────────────────────
        # Count total lines once to compute starting offset
        # ─────────────────────────────────────────────
        try:
            with open(path, "r") as f:
                total_lines = sum(1 for _ in f)
        except Exception:
            total_lines = 0

        start_line = max(0, total_lines - keep_last)

        # ─────────────────────────────────────────────
        # Stream only the most recent `keep_last` events
        # ─────────────────────────────────────────────
        with open(path, "r") as f:
            for line in islice(f, start_line, None):
                try:
                    j = json.loads(line)
                    sym = j.get("choice") or j.get("correct")
                    if not sym or len(sym) > 2 or sym not in valid_syms:
                        continue
                    self.observe(sym)
                    event_count += 1
                except Exception:
                    continue

        # ─────────────────────────────────────────────
        # Persist learned temporal model
        # ─────────────────────────────────────────────
        self.save_temporal_model()

        total_events = sum(sum(v.values()) for v in self.markov_graph.values())
        print(f"🧩 Learned {len(self.markov_graph)} unique transitions across {total_events} events.")
        print(f"📈 Processed {event_count} most recent PAL events (streamed mode).")

    # ─────────────────────────────────────────────
    # Live resonance feedback update (PAL coupling)
    # ─────────────────────────────────────────────
    def update(self, prev_symbol: str, next_symbol: str, reward: float = 1.0, vec: List[float] | None = None):
        """
        Update predictive transition weights from observed symbol sequence.
        Handles tuple-key encoding safely and maintains weighted counts.
        """
        key = (prev_symbol, next_symbol)

        # Initialize transition entries safely
        if key not in self.transitions:
            self.transitions[key] = 0.0
        if key not in self.counts:
            self.counts[key] = 0

        # Weighted reinforcement update (resonance-modulated)
        delta = reward * 0.5 + 0.5
        self.transitions[key] += delta
        self.counts: Dict[Tuple[str, str], int] = defaultdict(int)
        self.counts[key] += 1

        self._append_prediction_event(
            "predictive_transition",
            {"prev": prev_symbol, "next": next_symbol, "reward": reward},
        )

        # Optional diagnostic output
        if getattr(self, "verbose", False):
            print(f"🧩 Updated transition {prev_symbol} -> {next_symbol} "
                  f"(Δ={delta:.3f}, total={self.transitions[key]:.3f}, count={self.counts[key]})")

        # Apply small decay to all transitions for temporal smoothing
        for k in list(self.transitions.keys()):
            self.transitions[k] *= 0.999

    # ─────────────────────────────────────────────
    # Predict next likely symbol
    # ─────────────────────────────────────────────
    def predict_next(self, current_choice: str) -> Tuple[str, float]:
        """Return the next expected symbol using resonance + Markov weights."""
        # Priority: dynamic resonance transitions
        candidates = [(b, w) for (a, b), w in self.transitions.items() if a == current_choice]
        if not candidates and self.markov_graph:
            # fallback to Markov probabilities
            dist = self.markov_graph.get(current_choice, {})
            if dist:
                total = sum(dist.values())
                ranked = sorted(dist.items(), key=lambda x: x[1], reverse=True)
                choice, count = ranked[0]
                prob = count / total
                self.last_prediction = choice
                self.prediction_confidence = prob
                return choice, prob

        if not candidates:
            self.last_prediction = random.choice([c for (_, c) in self.transitions.keys()] or ["Ω", "λ", "Φ"])
            self.prediction_confidence = 0.1
            return self.last_prediction, 0.1

        total = sum(w for _, w in candidates)
        probs = [(b, w / total) for b, w in candidates]
        choice, p = max(probs, key=lambda x: x[1])
        self.last_prediction = choice
        self.prediction_confidence = p
        return choice, p

    # ─────────────────────────────────────────────
    # Evaluate prediction accuracy
    # ─────────────────────────────────────────────
    def evaluate(self, actual_choice: str) -> float:
        """Compare actual outcome vs last prediction and log temporal feedback."""
        if not self.last_prediction:
            return 0.0

        # basic success metric
        success = 1.0 if self.last_prediction == actual_choice else 0.0
        self.prediction_confidence = 0.9 * self.prediction_confidence + 0.1 * success

        # ─────────────────────────────────────────────
        # Temporal feedback logging
        # ─────────────────────────────────────────────
        try:
            self._append_prediction_event(
                "predictive_evaluation",
                {
                    "predicted": self.last_prediction,
                    "actual": actual_choice,
                    "temporal_pred": getattr(self.tcm, "last_prediction", None),
                    "success": success,
                    "confidence": self.prediction_confidence,
                },
            )
        except Exception as e:
            print(f"⚠️ Failed to log predictive result: {e}")

        return success

    # ─────────────────────────────────────────────
    # Apply PAL reinforcement feedback
    # ─────────────────────────────────────────────
    def apply_pal_feedback(self, reward: float):
        """
        Adjust prediction confidence based on PAL reward feedback.
        Reward ∈ [0,1] increases or decreases bias weight slightly.
        """
        try:
            delta = (reward - 0.5) * 0.05
            self.prediction_confidence = max(0.0, min(1.0, self.prediction_confidence + delta))
        except Exception as e:
            print(f"⚠️ apply_pal_feedback error: {e}")

    # ─────────────────────────────────────────────
    # Save temporal model (Markov graph)
    # ─────────────────────────────────────────────
    def save_temporal_model(self, path=None):
        out = {k: dict(v) for k, v in self.markov_graph.items()}
        if self.vault_store.enabled and path is None:
            self.vault_store.put_state("predictive_temporal_model", {"markov_graph": out})
            return
        path = Path(path or self.model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"🧮 Temporal model saved -> {path}")

    # ─────────────────────────────────────────────
    # Save predictive bias (resonance state)
    # ─────────────────────────────────────────────
    def save_state(self):
        """Safely serialize predictive bias state with tuple-key encoding."""
        
        # Helper to convert tuple keys -> string "A->B"
        def _encode_keys(d):
            return {f"{k[0]}->{k[1]}": v for k, v in d.items()}

        # Build export data
        data = {
            "window_size": getattr(self, "window_size", None),
            "transitions": _encode_keys(getattr(self, "transitions", {})),
            "counts": _encode_keys(getattr(self, "counts", {})),
            "confidence": getattr(self, "prediction_confidence", {}),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if self.vault_store.enabled:
            self.vault_store.put_state("predictive_bias_state", data)
        else:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w") as f:
                json.dump(data, f, indent=2)

        location = "vault://learning.customer_state/predictive_bias_state" if self.vault_store.enabled else self.state_path.name
        print(f"💾 PredictiveBias saved -> {location} ({len(self.transitions)} transitions)")

    def load_state(self):
        """Load predictive bias state safely with tuple-key decoding and auto-heal."""
        if self.vault_store.enabled:
            data = self.vault_store.get_state("predictive_bias_state", None)
            if data is None:
                print("⚠️ No predictive state found - creating fresh baseline.")
                self.save_state()
                return
        elif not self.state_path.exists():
            print("⚠️ No predictive state found - creating fresh baseline.")
            self.save_state()
            return

        def _decode_keys(d):
            out = {}
            for k, v in d.items():
                if isinstance(k, str) and "->" in k:
                    a, b = k.split("->", 1)
                    out[(a, b)] = v
            return out

        try:
            if not self.vault_store.enabled:
                with open(self.state_path, "r") as f:
                    data = json.load(f)

            self.window_size = data.get("window_size", self.window_size)
            self.transitions = _decode_keys(data.get("transitions", {}))
            self.counts = _decode_keys(data.get("counts", {}))
            self.prediction_confidence = data.get("confidence", 0.0)

            print(f"🔁 PredictiveBias state restored -> {len(self.transitions)} transitions")

        except json.JSONDecodeError as e:
            print(f"⚠️ Corrupted predictive_bias_state.json detected: {e}")
            if not self.vault_store.enabled:
                backup = self.state_path.with_suffix(".corrupt.json")
                self.state_path.rename(backup)
                print(f"🩹 Backup saved -> {backup.name}, regenerating fresh state...")
            self.save_state()
        except Exception as e:
            print(f"⚠️ Unexpected error loading predictive state: {e}")
            self.save_state()

    # ─────────────────────────────────────────────
    # Summarize learned transitions
    # ─────────────────────────────────────────────
    def summarize(self, top_n=10):
        print("\n🔮 Predictive Transition Summary")
        sorted_trans = sorted(self.transitions.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        for (a, b), w in sorted_trans:
            print(f"  {a} -> {b}  (w={w:.3f})")
        print(f"📈 Confidence: {self.prediction_confidence:.3f}")

    # ─────────────────────────────────────────────
    # Temporal Coherence Memory (delegation)
    # ─────────────────────────────────────────────
    def observe_temporal(self, symbol: str):
        """Feed symbol into temporal sequence buffer and reinforce on correct predictions."""
        self.tcm.update_sequence(symbol)

        # ─────────────────────────────────────────────
        # Temporal Coherence Feedback Loop
        # ─────────────────────────────────────────────
        if len(self.tcm.sequence_buffer) >= 2:
            last_sym = self.tcm.sequence_buffer[-2]
            pred = self.tcm.predict_next()
            if pred == symbol:
                # reinforce both layers on successful temporal prediction
                self.tcm.reinforce(last_sym, symbol)
                self.prediction_confidence = min(1.0, self.prediction_confidence + 0.01)

    def predict_temporal_next(self) -> str | None:
        """Predict next symbol using temporal coherence memory."""
        return self.tcm.predict_next()

    def reinforce_temporal(self, last_symbol: str, actual_symbol: str):
        """Reinforce TCM when prediction == actual."""
        self.tcm.reinforce(last_symbol, actual_symbol)

# ─────────────────────────────────────────────
# Demonstration utility (manual test)
# ─────────────────────────────────────────────
def run_predictive_cycle(n=12):
    pb = PredictiveBias()
    pb.train_from_events()
    pb.load_state()

    if not pb.markov_graph and not pb.transitions:
        print("⚠️ No transitions learned yet.")
        return

    keys = list(pb.markov_graph.keys()) or [a for (a, _) in pb.transitions.keys()]
    cur = random.choice(keys)
    print(f"🔹 Starting symbol: {cur}")
    for i in range(n):
        nxt, prob = pb.predict_next(cur)
        print(f"-> predicts {nxt}  (p≈{prob:.2f})")
        pb.update("demo", nxt, reward=1.0, vec=[0.1, 0.2, 0.3, 0.9, 0.1])
        pb.evaluate(nxt)
        cur = nxt

    pb.save_state()
    pb.summarize()

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run or update the Predictive Bias Layer.")
    parser.add_argument(
        "--mode",
        choices=["run", "update"],
        default="run",
        help="Choose 'run' for demo cycle or 'update' to retrain from PAL events."
    )
    args = parser.parse_args()

    if args.mode == "update":
        print("🔁 Updating PredictiveBias transitions from latest PAL events...")
        pb = PredictiveBias()
        pb.load_state()        # <── add this before training to retain history
        pb.train_from_events()
        pb.save_state()
        print("✅ PredictiveBias update complete.")
        sys.exit(0)
    else:
        run_predictive_cycle(12)
