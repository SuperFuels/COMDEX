#!/usr/bin/env python3
"""Regression tests for the finite damped-Chebyshev amplifier."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rh_frontier_chebyshev_amplifier import (  # noqa: E402
    critical_pair_contribution,
    quartet_contribution,
    u_of,
)


class ChebyshevAmplifierTests(unittest.TestCase):
    def setUp(self) -> None:
        mp.mp.dps = 80
        self.gamma = mp.im(mp.zetazero(1))

    def test_critical_background_is_nonnegative(self) -> None:
        target = mp.mpc("0.5001", self.gamma)
        critical = mp.mpc("0.5", self.gamma)
        value = critical_pair_contribution(
            critical, mp.re(u_of(target)), damping=10, mode=33
        )
        self.assertGreaterEqual(value, 0)

    def test_tuned_off_line_quartet_is_negative(self) -> None:
        target = mp.mpc("0.5001", self.gamma)
        value = quartet_contribution(
            target, mp.re(u_of(target)), damping=10, mode=33
        )
        self.assertLess(value, 0)


if __name__ == "__main__":
    unittest.main()
