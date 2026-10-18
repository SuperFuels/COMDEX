from __future__ import annotations

import argparse
import io
import re
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Callable, Optional

from symatics_pi_test import run as run_pi
from symatics_coherence_test import run as run_coherence
from symatics_energy_info_test import run as run_energy_info
from symatics_resonance_test import run as run_resonance


@dataclass
class TestResult:
    name: str
    passed: Optional[bool]
    summary: str
    body: str


def _capture_output(fn: Callable, *args, **kwargs) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue().strip()


def _extract_bool(text: str, key: str) -> Optional[bool]:
    m = re.search(rf"{re.escape(key)}\s*:\s*(True|False)", text)
    if not m:
        return None
    return m.group(1) == "True"


def _extract_float(text: str, key: str) -> Optional[float]:
    m = re.search(rf"{re.escape(key)}\s*:\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", text)
    if not m:
        return None
    return float(m.group(1))


def _extract_minimum_line(text: str) -> Optional[str]:
    m = re.search(r"--- MINIMUM ---\n(.+)", text)
    if not m:
        return None
    return m.group(1).strip()


def _run_pi(path: str) -> TestResult:
    body = _capture_output(run_pi, path)
    minimum = _extract_minimum_line(body)

    if minimum:
        summary = f"minimum located: {minimum}"
    else:
        summary = "minimum not found"

    # PI is informational / diagnostic, not strict pass/fail here.
    return TestResult(
        name="pi_notch",
        passed=None,
        summary=summary,
        body=body,
    )


def _run_coherence(path: str, min_coherence: float) -> TestResult:
    body = _capture_output(run_coherence, path, min_coherence=min_coherence)
    passed = _extract_bool(body, "passed_any")
    threshold = _extract_float(body, "threshold")
    tested = _extract_float(body, "tested rows")

    tested_str = "?" if tested is None else str(int(tested))
    thr_str = "?" if threshold is None else f"{threshold:.6f}"

    summary = f"tested={tested_str} threshold={thr_str} passed_any={passed}"
    return TestResult(
        name="coherence_information",
        passed=passed,
        summary=summary,
        body=body,
    )


def _run_energy_info(path: str) -> TestResult:
    body = _capture_output(run_energy_info, path)
    mean_ei = _extract_float(body, "mean(E*I)")
    std_ei = _extract_float(body, "std(E*I)")
    cv_ei = _extract_float(body, "cv(E*I)")
    tested = _extract_float(body, "tested rows")

    tested_str = "?" if tested is None else str(int(tested))
    mean_str = "?" if mean_ei is None else f"{mean_ei:.6f}"
    std_str = "?" if std_ei is None else f"{std_ei:.6f}"
    cv_str = "?" if cv_ei is None else f"{cv_ei:.6f}"

    summary = f"tested={tested_str} mean(E*I)={mean_str} std={std_str} cv={cv_str}"
    return TestResult(
        name="energy_information_duality",
        passed=None,
        summary=summary,
        body=body,
    )


def _run_resonance(
    path: str,
    max_drift: float,
    min_coherence: float,
    max_boundedness: float,
) -> TestResult:
    body = _capture_output(
        run_resonance,
        path,
        max_drift=max_drift,
        min_coherence=min_coherence,
        max_boundedness=max_boundedness,
    )
    passed = _extract_bool(body, "passed_any")
    tested = _extract_float(body, "tested rows")

    tested_str = "?" if tested is None else str(int(tested))
    summary = (
        f"tested={tested_str} "
        f"max_drift={max_drift:.6f} "
        f"min_coherence={min_coherence:.6f} "
        f"max_boundedness={max_boundedness:.6f} "
        f"passed_any={passed}"
    )
    return TestResult(
        name="resonance_stability",
        passed=passed,
        summary=summary,
        body=body,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--max-drift", type=float, default=0.02)
    ap.add_argument("--min-coherence", type=float, default=0.95)
    ap.add_argument("--max-boundedness", type=float, default=1.25)
    ap.add_argument(
        "--show-sections",
        action="store_true",
        help="Print the full output of each sub-test after the consolidated summary.",
    )
    args = ap.parse_args()

    results = [
        _run_pi(args.input),
        _run_coherence(args.input, min_coherence=args.min_coherence),
        _run_energy_info(args.input),
        _run_resonance(
            args.input,
            max_drift=args.max_drift,
            min_coherence=max(0.90, args.min_coherence),
            max_boundedness=args.max_boundedness,
        ),
    ]

    print("\n=== SYMATICS CONSOLIDATED BASELINE REPORT ===\n")
    print(f"input: {args.input}\n")

    for r in results:
        status = "INFO"
        if r.passed is True:
            status = "PASS"
        elif r.passed is False:
            status = "FAIL"

        print(f"[{status}] {r.name}")
        print(f"  {r.summary}\n")

    if args.show_sections:
        for r in results:
            print(f"=== RAW SECTION: {r.name} ===\n")
            print(r.body)
            print("")


if __name__ == "__main__":
    main()