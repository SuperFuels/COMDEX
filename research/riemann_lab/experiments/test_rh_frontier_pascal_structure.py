#!/usr/bin/env python3
"""Fast tests for the exact and interval parts of Pascal-structure mining."""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rh_frontier_pascal_structure import (  # noqa: E402
    arb_bounds,
    closed_form_coefficients,
    transformed_coefficients,
    verify_exact_identity,
)


class PascalStructureTests(unittest.TestCase):
    def test_arb_midpoint_radius_parser(self) -> None:
        self.assertEqual(
            arb_bounds("[1.25 +/- 0.05]"),
            (Decimal("1.20"), Decimal("1.30")),
        )

    def test_exact_kernel_example(self) -> None:
        self.assertEqual(
            transformed_coefficients(5, 3, 6),
            closed_form_coefficients(5, 3, 6),
        )
        self.assertEqual(
            closed_form_coefficients(5, 3, 6),
            [30, 15, 7, 3, 1, 0],
        )

    def test_exact_identity_grid(self) -> None:
        report = verify_exact_identity(8)
        self.assertEqual(report["matrix_entries_checked"], 36)


if __name__ == "__main__":
    unittest.main()
