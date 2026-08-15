#!/usr/bin/env python3
"""Fast regression tests for the incremental Gram rover."""

from __future__ import annotations

import unittest
import sys
import tempfile
from pathlib import Path

from flint import ctx

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rh_frontier_gram_rover import execute_attempt
from rh_frontier_gram_rover import IncrementalLDL, gram_entry, overlaps
from rh_frontier_gram_rover_block import load_state, save_json_atomic, serialize_state
from rh_frontier_li_full_arb import certified_li_coefficients
from rh_frontier_li_coefficient_cache import (
    bootstrap_cache_from_rover_state,
    extend_cache,
)


class GramRoverTests(unittest.TestCase):
    def test_full_lane_and_adversarial_stop_certificate(self) -> None:
        ctx.dps = 120
        result = execute_attempt(
            count=12,
            digits=120,
            checkpoint_every=6,
            progress_every=0,
            gamma="14.134725141734693790457251983562",
            betas=["0.51"],
        )
        lanes = {lane["name"]: lane for lane in result["lanes"]}
        self.assertEqual(lanes["unmodified_full_li"]["status"], "completed_finite_range")
        self.assertTrue(
            all(checkpoint["intervals_overlap"]
                for checkpoint in lanes["unmodified_full_li"]["checkpoints"])
        )
        control = lanes["synthetic_beta_0.51"]
        self.assertEqual(control["status"], "halted_negative")
        self.assertEqual(control["stop_certificate"]["order"], 11)
        self.assertTrue(control["stop_certificate"]["quadratic_form_certified_negative"])

    def test_stage_hash_chain(self) -> None:
        result = execute_attempt(
            count=8,
            digits=100,
            checkpoint_every=4,
            progress_every=0,
            gamma="14.134725141734693790457251983562",
            betas=[],
        )
        stages = result["lanes"][0]["stages"]
        self.assertEqual(stages[0]["previous_stage_hash"], "0" * 64)
        for previous, current in zip(stages, stages[1:]):
            self.assertEqual(current["previous_stage_hash"], previous["stage_hash"])

    def test_persistent_factor_round_trip(self) -> None:
        ctx.dps = 100
        coefficients = certified_li_coefficients(8, 100)
        factor = IncrementalLDL()
        for n in range(1, 9):
            border = [gram_entry(coefficients, i, n) for i in range(1, n)]
            pivot, _ = factor.extend(border, gram_entry(coefficients, n, n))
            self.assertTrue(pivot > 0)
        state = serialize_state(factor, coefficients, 8, 100, "a" * 64, [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json.gz"
            save_json_atomic(path, state)
            loaded, restored, cached = load_state(path, 100)
        self.assertEqual(loaded["completed_order"], 8)
        self.assertEqual(len(restored.pivots), 8)
        self.assertEqual(len(cached), 9)
        self.assertTrue(all(overlaps(left, right) for left, right in zip(factor.pivots, restored.pivots)))

    def test_coefficient_cache_extends_and_matches_direct_construction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "coefficients.json.gz"
            first_payload, first = extend_cache(cache_path, 8, 100)
            second_payload, extended = extend_cache(cache_path, 14, 100)
            direct = certified_li_coefficients(14, 100)
        self.assertEqual(first_payload["count"], 8)
        self.assertEqual(second_payload["count"], 14)
        self.assertTrue(
            all(overlaps(left, right) for left, right in zip(extended, direct))
        )

    def test_cache_bootstraps_from_rover_state_and_extends(self) -> None:
        ctx.dps = 120
        coefficients = certified_li_coefficients(10, 120)
        factor = IncrementalLDL()
        for n in range(1, 11):
            border = [gram_entry(coefficients, i, n) for i in range(1, n)]
            pivot, _ = factor.extend(border, gram_entry(coefficients, n, n))
            self.assertTrue(pivot > 0)
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json.gz"
            cache_path = Path(directory) / "cache.json.gz"
            state = serialize_state(factor, coefficients, 10, 120, "b" * 64, [])
            save_json_atomic(state_path, state)
            bootstrapped = bootstrap_cache_from_rover_state(
                state_path, cache_path, 120
            )
            extended_payload, extended = extend_cache(cache_path, 14, 120)
            direct = certified_li_coefficients(14, 120)
        self.assertEqual(bootstrapped["count"], 10)
        self.assertEqual(extended_payload["count"], 14)
        self.assertTrue(
            all(overlaps(left, right) for left, right in zip(extended, direct))
        )


if __name__ == "__main__":
    unittest.main()
