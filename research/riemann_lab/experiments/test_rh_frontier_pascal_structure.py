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
from rh_frontier_pascal_toeplitz import verify as verify_toeplitz  # noqa: E402
from rh_frontier_toeplitz_quartet_detector import analyse_case  # noqa: E402


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

    def test_toeplitz_generating_function_grid(self) -> None:
        report = verify_toeplitz(8)
        self.assertEqual(report["coefficient_pairs_checked"], 64)

    def test_three_lag_quartet_control(self) -> None:
        critical = analyse_case("0.5", "14.134725141734693790457251983562")
        off_line = analyse_case("0.51", "14.134725141734693790457251983562")
        self.assertEqual(Decimal(critical["determinant_3x3"]), 0)
        self.assertTrue(off_line["determinant_negative"])


if __name__ == "__main__":
    unittest.main()
