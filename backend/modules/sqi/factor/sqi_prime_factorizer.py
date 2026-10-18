from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from math import gcd, isqrt
from pathlib import Path
from random import Random
from time import perf_counter, time
from typing import Any, Dict, Iterable, List, Optional, Tuple


SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29,
    31, 37, 41, 43, 47
]

TRACE_DIR = Path(".runtime/sqi_factor_traces")
BENCHMARK_DIR = Path("benchmarks")


@dataclass(frozen=True)
class FactorBranch:
    candidate: int
    depth: int
    residues: Dict[int, int] = field(default_factory=dict)
    coherence: float = 0.0
    reason: str = ""


@dataclass
class FactorCollapseTrace:
    n: int
    found_factor: Optional[int]
    cofactor: Optional[int]
    method: str
    checked: int
    branches_generated: int
    branches_pruned: int
    elapsed_ms: float
    trace: List[Dict[str, Any]]
    trace_path: Optional[str] = None
    dashboard_path: Optional[str] = None


@dataclass
class StrategyState:
    name: str
    checked: int = 0
    branches_generated: int = 0
    branches_pruned: int = 0
    done: bool = False
    found_factor: Optional[int] = None
    cofactor: Optional[int] = None
    coherence: float = 0.0
    last_event: Dict[str, Any] = field(default_factory=dict)


def _now_ms() -> int:
    return int(time() * 1000)


def _safe_slug(value: int) -> str:
    return str(value).replace("-", "neg")


def write_jsonl_event(path: Path, event: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts_ms": _now_ms(), **event}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")


def write_dashboard_snapshot(
    path: Path,
    n: int,
    states: Dict[str, StrategyState],
    final: Optional[FactorCollapseTrace] = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "n": n,
        "updated_ts_ms": _now_ms(),
        "strategies": {
            name: asdict(state)
            for name, state in states.items()
        },
        "final": asdict(final) if final else None,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def exact_factor(n: int, d: Optional[int]) -> bool:
    return bool(d and d not in (1, n) and n % d == 0)


def miller_rabin_is_probable_prime(n: int) -> bool:
    """
    Deterministic Miller-Rabin for 64-bit integers.

    For larger integers, this is still a strong probable-prime test using
    the same bases, but the deterministic guarantee is only for n < 2^64.
    """
    if n < 2:
        return False

    for p in SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False

    # Write n-1 = d * 2^s
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2

    # Deterministic bases for testing 64-bit integers.
    bases = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]

    for a in bases:
        if a >= n:
            continue

        x = pow(a, d, n)
        if x in (1, n - 1):
            continue

        witness_found = True
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                witness_found = False
                break

        if witness_found:
            return False

    return True


def naive_trial_factor(n: int) -> Tuple[Optional[int], int]:
    if n < 2:
        return None, 0

    if n % 2 == 0:
        return 2, 1

    checks = 1
    limit = isqrt(n)
    d = 3

    while d <= limit:
        checks += 1
        if n % d == 0:
            return d, checks
        d += 2

    return None, checks


def wheel_candidates(limit: int) -> Iterable[int]:
    d = 7
    while d <= limit:
        if d % 2 and d % 3 and d % 5:
            yield d
        d += 2


def wheel_only_factor(n: int) -> Tuple[Optional[int], int]:
    if n % 2 == 0:
        return 2, 1
    if n % 3 == 0:
        return 3, 1
    if n % 5 == 0:
        return 5, 1

    checks = 0
    for d in wheel_candidates(isqrt(n)):
        checks += 1
        if n % d == 0:
            return d, checks

    return None, checks


def score_branch(n: int, d: int, depth: int) -> FactorBranch:
    residues = {p: d % p for p in SMALL_PRIMES[:8]}

    for p in SMALL_PRIMES[:8]:
        if d != p and d % p == 0:
            return FactorBranch(
                candidate=d,
                depth=depth,
                residues=residues,
                coherence=0.0,
                reason=f"pruned: candidate divisible by small prime {p}",
            )

    rem = n % d

    if rem == 0:
        return FactorBranch(
            candidate=d,
            depth=depth,
            residues=residues,
            coherence=1.0,
            reason="exact divisor collapse",
        )

    closeness = min(rem, d - rem) / d
    closeness_score = 1.0 - closeness
    depth_penalty = min(depth / 10_000, 0.25)

    coherence = max(0.0, min(0.99, 0.55 * closeness_score - depth_penalty))

    return FactorBranch(
        candidate=d,
        depth=depth,
        residues=residues,
        coherence=coherence,
        reason=f"residue closeness rem={rem}",
    )


def estimate_factor_strategy(n: int) -> Dict[str, Any]:
    root = isqrt(n)
    ceil_root = root if root * root == n else root + 1
    gap = ceil_root * ceil_root - n
    scale = max(1, ceil_root)
    near_square_score = max(0.0, 1.0 - (gap / scale))
    rho_score = 1.0 - near_square_score

    if near_square_score >= 0.98:
        order = ["fermat", "brent_rho", "pollard_rho", "sqi_wheel"]
    else:
        order = ["brent_rho", "pollard_rho", "fermat", "sqi_wheel"]

    return {
        "ceil_sqrt": ceil_root,
        "near_square_gap": gap,
        "near_square_score": round(near_square_score, 6),
        "rho_score": round(rho_score, 6),
        "order": order,
    }


def fermat_factor(n: int, max_steps: int = 100_000) -> Tuple[Optional[int], int, List[Dict[str, Any]]]:
    trace: List[Dict[str, Any]] = []

    if n % 2 == 0:
        return 2, 1, [{"event": "fermat_even", "factor": 2}]

    a = isqrt(n)
    if a * a < n:
        a += 1

    for step in range(max_steps):
        b2 = a * a - n
        b = isqrt(b2)

        if b * b == b2:
            f1 = a - b
            f2 = a + b

            if exact_factor(n, f1):
                trace.append({
                    "event": "fermat_collapse",
                    "a": a,
                    "b": b,
                    "factor": f1,
                    "cofactor": f2,
                    "steps": step + 1,
                })
                return f1, step + 1, trace

        if step < 5 or step % 1000 == 0:
            trace.append({
                "event": "fermat_probe",
                "step": step,
                "a": a,
                "b2": b2,
            })

        a += 1

    return None, max_steps, trace[-10:]


def pollard_rho_factor(
    n: int,
    seed: int = 2,
    c: int = 1,
    max_steps: int = 100_000,
) -> Tuple[Optional[int], int, List[Dict[str, Any]]]:
    trace: List[Dict[str, Any]] = []

    if n % 2 == 0:
        return 2, 1, [{"event": "rho_even", "factor": 2}]

    def f(x: int) -> int:
        return (x * x + c) % n

    x = seed % n
    y = seed % n

    for step in range(1, max_steps + 1):
        x = f(x)
        y = f(f(y))
        d = gcd(abs(x - y), n)

        if step <= 5 or step % 1000 == 0:
            trace.append({
                "event": "rho_probe",
                "step": step,
                "seed": seed,
                "c": c,
                "gcd": d,
            })

        if d == n:
            return None, step, trace[-10:]

        if exact_factor(n, d):
            trace.append({
                "event": "rho_collapse",
                "step": step,
                "seed": seed,
                "c": c,
                "factor": d,
                "cofactor": n // d,
            })
            return d, step, trace

    return None, max_steps, trace[-10:]


def brent_rho_factor(
    n: int,
    seed: int = 2,
    c: int = 1,
    max_steps: int = 100_000,
) -> Tuple[Optional[int], int, List[Dict[str, Any]]]:
    """
    Brent variant of Pollard Rho.

    Usually faster than classic Floyd-cycle Pollard Rho because it batches gcd work.
    """
    trace: List[Dict[str, Any]] = []

    if n % 2 == 0:
        return 2, 1, [{"event": "brent_even", "factor": 2}]

    y = seed % n
    r = 1
    q = 1
    m = 128
    g = 1
    checked = 0

    def f(x: int) -> int:
        return (x * x + c) % n

    while g == 1 and checked < max_steps:
        x = y
        for _ in range(r):
            y = f(y)
            checked += 1
            if checked >= max_steps:
                break

        k = 0
        while k < r and g == 1 and checked < max_steps:
            ys = y
            for _ in range(min(m, r - k)):
                y = f(y)
                q = (q * abs(x - y)) % n
                checked += 1
                if checked >= max_steps:
                    break

            g = gcd(q, n)
            k += m

            if checked <= 5 or checked % 1000 == 0:
                trace.append({
                    "event": "brent_probe",
                    "checked": checked,
                    "seed": seed,
                    "c": c,
                    "gcd": g,
                    "r": r,
                })

        r *= 2

    if g == n:
        g = 1
        while g == 1 and checked < max_steps:
            ys = f(ys)
            g = gcd(abs(x - ys), n)
            checked += 1

    if exact_factor(n, g):
        trace.append({
            "event": "brent_collapse",
            "checked": checked,
            "seed": seed,
            "c": c,
            "factor": g,
            "cofactor": n // g,
        })
        return g, checked, trace

    return None, checked, trace[-10:]


class FermatStepper:
    def __init__(self, n: int):
        self.n = n
        self.a = isqrt(n)
        if self.a * self.a < n:
            self.a += 1
        self.checked = 0

    def step(self, budget: int) -> Tuple[Optional[int], int, List[Dict[str, Any]]]:
        trace = []
        for _ in range(budget):
            b2 = self.a * self.a - self.n
            b = isqrt(b2)
            self.checked += 1

            if b * b == b2:
                f1 = self.a - b
                if exact_factor(self.n, f1):
                    trace.append({
                        "event": "fermat_collapse",
                        "a": self.a,
                        "b": b,
                        "factor": f1,
                        "cofactor": self.n // f1,
                        "steps": self.checked,
                    })
                    return f1, self.checked, trace

            if self.checked <= 5 or self.checked % 1000 == 0:
                trace.append({
                    "event": "fermat_probe",
                    "step": self.checked,
                    "a": self.a,
                    "b2": b2,
                })

            self.a += 1

        return None, self.checked, trace[-5:]


class BrentStepper:
    """
    Restartable Brent branch, executed in small seed branches.

    For interleaving, each call runs one Brent factor attempt with bounded steps.
    """
    def __init__(self, n: int, seed: int, c: int, max_steps: int):
        self.n = n
        self.seed = seed
        self.c = c
        self.max_steps = max_steps
        self.done = False
        self.checked = 0

    def step(self, budget: int) -> Tuple[Optional[int], int, List[Dict[str, Any]]]:
        if self.done:
            return None, self.checked, []

        f, checks, trace = brent_rho_factor(
            self.n,
            seed=self.seed,
            c=self.c,
            max_steps=min(self.max_steps, budget),
        )
        self.checked += checks
        self.done = True
        return f, self.checked, trace


class PollardStepper:
    def __init__(self, n: int, seed: int, c: int, max_steps: int):
        self.n = n
        self.seed = seed
        self.c = c
        self.max_steps = max_steps
        self.done = False
        self.checked = 0

    def step(self, budget: int) -> Tuple[Optional[int], int, List[Dict[str, Any]]]:
        if self.done:
            return None, self.checked, []

        f, checks, trace = pollard_rho_factor(
            self.n,
            seed=self.seed,
            c=self.c,
            max_steps=min(self.max_steps, budget),
        )
        self.checked += checks
        self.done = True
        return f, self.checked, trace


class WheelStepper:
    def __init__(self, n: int):
        self.n = n
        self.iterator = iter(wheel_candidates(isqrt(n)))
        self.depth = 0
        self.checked = 0
        self.generated = 0
        self.pruned = 0

    def step(self, budget: int) -> Tuple[Optional[int], int, List[Dict[str, Any]]]:
        trace = []
        top: List[FactorBranch] = []

        for _ in range(budget):
            try:
                d = next(self.iterator)
            except StopIteration:
                break

            branch = score_branch(self.n, d, self.depth)
            self.depth += 1
            self.generated += 1

            if branch.coherence <= 0.0:
                self.pruned += 1
                continue

            self.checked += 1
            top.append(branch)

            if branch.coherence >= 1.0 and self.n % d == 0:
                trace.append({
                    "event": "wheel_collapse",
                    "factor": d,
                    "cofactor": self.n // d,
                    "coherence": branch.coherence,
                    "reason": branch.reason,
                    "checked": self.checked,
                })
                return d, self.checked, trace

        top = sorted(top, key=lambda b: b.coherence, reverse=True)[:5]
        if top:
            trace.append({
                "event": "wheel_probe",
                "checked": self.checked,
                "generated": self.generated,
                "pruned": self.pruned,
                "top_candidates": [
                    {
                        "candidate": b.candidate,
                        "coherence": round(b.coherence, 6),
                        "reason": b.reason,
                    }
                    for b in top
                ],
            })

        return None, self.checked, trace


def make_result(
    *,
    n: int,
    factor: Optional[int],
    method: str,
    checked: int,
    branches_generated: int,
    branches_pruned: int,
    elapsed_ms: float,
    trace: List[Dict[str, Any]],
    trace_path: Optional[Path],
    dashboard_path: Optional[Path],
) -> FactorCollapseTrace:
    return FactorCollapseTrace(
        n=n,
        found_factor=factor,
        cofactor=n // factor if exact_factor(n, factor) else None,
        method=method,
        checked=checked,
        branches_generated=branches_generated,
        branches_pruned=branches_pruned,
        elapsed_ms=elapsed_ms,
        trace=trace,
        trace_path=str(trace_path) if trace_path else None,
        dashboard_path=str(dashboard_path) if dashboard_path else None,
    )


def sqi_factor_once(
    n: int,
    beam_width: int = 64,
    max_rounds: int = 10_000,
    rho_branches: int = 8,
    trace_jsonl: bool = True,
    dashboard_json: bool = True,
    fermat_step_budget: int = 256,
    rho_step_budget: int = 25_000,
    rho_active_branches: int = 2,
) -> FactorCollapseTrace:
    """
    Multi-branch SQI factor search.

    Version 2:
    - Miller-Rabin prime gate
    - adaptive routing
    - Brent Rho
    - interleaved branch-budget scheduling
    - JSONL trace artifacts
    - dashboard JSON snapshot
    """
    start = perf_counter()
    trace: List[Dict[str, Any]] = []

    if n < 2:
        raise ValueError("n must be >= 2")

    trace_path = TRACE_DIR / f"sqi_factor_{_safe_slug(n)}_{_now_ms()}.jsonl" if trace_jsonl else None
    dashboard_path = TRACE_DIR / f"sqi_factor_{_safe_slug(n)}_dashboard.json" if dashboard_json else None

    def emit(event: Dict[str, Any]) -> None:
        trace.append(event)
        if trace_path:
            write_jsonl_event(trace_path, {"n": n, **event})

    emit({"event": "start", "n": n})

    if miller_rabin_is_probable_prime(n):
        elapsed = (perf_counter() - start) * 1000
        emit({"event": "prime_gate", "n": n, "probable_prime": True})
        result = make_result(
            n=n,
            factor=None,
            method="prime",
            checked=1,
            branches_generated=1,
            branches_pruned=0,
            elapsed_ms=elapsed,
            trace=trace,
            trace_path=trace_path,
            dashboard_path=dashboard_path,
        )
        if dashboard_path:
            write_dashboard_snapshot(dashboard_path, n, {}, result)
        return result

    for p in SMALL_PRIMES:
        if n % p == 0:
            elapsed = (perf_counter() - start) * 1000
            emit({"event": "collapse_small_prime", "factor": p, "cofactor": n // p})
            result = make_result(
                n=n,
                factor=p,
                method="small_prime",
                checked=1,
                branches_generated=1,
                branches_pruned=0,
                elapsed_ms=elapsed,
                trace=trace,
                trace_path=trace_path,
                dashboard_path=dashboard_path,
            )
            if dashboard_path:
                state = StrategyState("small_prime", checked=1, found_factor=p, cofactor=n // p, coherence=1.0)
                write_dashboard_snapshot(dashboard_path, n, {"small_prime": state}, result)
            return result

    routing = estimate_factor_strategy(n)
    emit({"event": "branch_routing", **routing})

    rng = Random(1337)

    states: Dict[str, StrategyState] = {
        "fermat": StrategyState("fermat"),
        "brent_rho": StrategyState("brent_rho"),
        "pollard_rho": StrategyState("pollard_rho"),
        "sqi_wheel": StrategyState("sqi_wheel"),
    }

    fermat = FermatStepper(n)
    wheel = WheelStepper(n)

    brent_steppers = [
        BrentStepper(
            n=n,
            seed=rng.randint(2, max(3, min(n - 2, 10_000))),
            c=rng.randint(1, 25),
            max_steps=25_000,
        )
        for _ in range(rho_branches)
    ]

    pollard_steppers = [
        PollardStepper(
            n=n,
            seed=rng.randint(2, max(3, min(n - 2, 10_000))),
            c=rng.randint(1, 25),
            max_steps=25_000,
        )
        for _ in range(rho_branches)
    ]

    ordered_methods = routing["order"]
    total_checked = 0
    total_generated = 1 + len(brent_steppers) + len(pollard_steppers)
    total_pruned = 0

    # Budget scheduling: interleave methods by routing order.
    # Near-square cases still give Fermat first chance, but spread cases give Rho first.
    per_branch_budget = {
        "fermat": fermat_step_budget,
        "brent_rho": rho_step_budget,
        "pollard_rho": rho_step_budget,
        "sqi_wheel": beam_width,
    }

    for round_i in range(max_rounds):
        for method in ordered_methods:
            factor: Optional[int] = None
            method_trace: List[Dict[str, Any]] = []
            checked_now = 0

            if method == "fermat":
                factor, checked_now, method_trace = fermat.step(per_branch_budget["fermat"])
                states["fermat"].checked = checked_now
                states["fermat"].branches_generated = 1

            elif method == "brent_rho":
                active = [s for s in brent_steppers if not s.done]
                if not active:
                    states["brent_rho"].done = True
                    continue

                for idx, stepper in enumerate(active[:rho_active_branches]):
                    factor, checked_now, method_trace = stepper.step(per_branch_budget["brent_rho"])
                    states["brent_rho"].checked += checked_now
                    states["brent_rho"].branches_generated += 1

                    if factor:
                        method_trace.append({"event": "brent_branch_index", "branch": idx})
                        break

            elif method == "pollard_rho":
                active = [s for s in pollard_steppers if not s.done]
                if not active:
                    states["pollard_rho"].done = True
                    continue

                for idx, stepper in enumerate(active[:rho_active_branches]):
                    factor, checked_now, method_trace = stepper.step(per_branch_budget["pollard_rho"])
                    states["pollard_rho"].checked += checked_now
                    states["pollard_rho"].branches_generated += 1

                    if factor:
                        method_trace.append({"event": "pollard_branch_index", "branch": idx})
                        break

            elif method == "sqi_wheel":
                factor, checked_now, method_trace = wheel.step(per_branch_budget["sqi_wheel"])
                states["sqi_wheel"].checked = checked_now
                states["sqi_wheel"].branches_generated = wheel.generated
                states["sqi_wheel"].branches_pruned = wheel.pruned
                total_pruned = wheel.pruned

            for ev in method_trace:
                emit({"event": "strategy_event", "method": method, "round": round_i, **ev})

            if method_trace:
                states[method].last_event = method_trace[-1]
                states[method].coherence = 1.0 if factor else min(0.99, states[method].coherence + 0.01)

            if dashboard_path and (round_i < 5 or round_i % 10 == 0):
                write_dashboard_snapshot(dashboard_path, n, states)

            if exact_factor(n, factor):
                elapsed = (perf_counter() - start) * 1000
                emit({
                    "event": "collapse",
                    "method": method,
                    "factor": factor,
                    "cofactor": n // factor,
                    "round": round_i,
                    "verified": True,
                })

                states[method].found_factor = factor
                states[method].cofactor = n // factor
                states[method].coherence = 1.0

                total_checked = sum(s.checked for s in states.values())
                total_generated += states["sqi_wheel"].branches_generated
                total_pruned = states["sqi_wheel"].branches_pruned

                result = make_result(
                    n=n,
                    factor=factor,
                    method=method,
                    checked=total_checked,
                    branches_generated=total_generated,
                    branches_pruned=total_pruned,
                    elapsed_ms=elapsed,
                    trace=trace,
                    trace_path=trace_path,
                    dashboard_path=dashboard_path,
                )
                if dashboard_path:
                    write_dashboard_snapshot(dashboard_path, n, states, result)
                return result

        if all(s.done for s in states.values() if s.name in ("brent_rho", "pollard_rho")):
            # Fermat and wheel may still run, but avoid infinite spread-case loops.
            if round_i > 20:
                break

    elapsed = (perf_counter() - start) * 1000
    emit({"event": "no_factor_found", "rounds": max_rounds})

    total_checked = sum(s.checked for s in states.values())
    total_generated += states["sqi_wheel"].branches_generated
    total_pruned = states["sqi_wheel"].branches_pruned

    result = make_result(
        n=n,
        factor=None,
        method="none",
        checked=total_checked,
        branches_generated=total_generated,
        branches_pruned=total_pruned,
        elapsed_ms=elapsed,
        trace=trace,
        trace_path=trace_path,
        dashboard_path=dashboard_path,
    )
    if dashboard_path:
        write_dashboard_snapshot(dashboard_path, n, states, result)
    return result


def factor_recursive(n: int) -> List[int]:
    if n < 2:
        return []

    if miller_rabin_is_probable_prime(n):
        return [n]

    result = sqi_factor_once(n)

    if result.found_factor is None:
        return [n]

    return factor_recursive(result.found_factor) + factor_recursive(result.cofactor)


def time_call(fn, *args, **kwargs) -> Dict[str, Any]:
    start = perf_counter()
    factor, checks = fn(*args, **kwargs)
    elapsed_ms = (perf_counter() - start) * 1000
    n = args[0]
    return {
        "factor": factor,
        "cofactor": n // factor if exact_factor(n, factor) else None,
        "checks": checks,
        "elapsed_ms": round(elapsed_ms, 4),
    }


def fermat_only_factor(n: int) -> Tuple[Optional[int], int]:
    f, checks, _ = fermat_factor(n, max_steps=100_000)
    return f, checks


def pollard_only_factor(n: int) -> Tuple[Optional[int], int]:
    rng = Random(1337)
    total = 0

    for _ in range(8):
        seed = rng.randint(2, max(3, min(n - 2, 10_000)))
        c = rng.randint(1, 25)
        f, checks, _ = pollard_rho_factor(n, seed=seed, c=c, max_steps=25_000)
        total += checks

        if exact_factor(n, f):
            return f, total

    return None, total


def brent_only_factor(n: int) -> Tuple[Optional[int], int]:
    rng = Random(1337)
    total = 0

    for _ in range(8):
        seed = rng.randint(2, max(3, min(n - 2, 10_000)))
        c = rng.randint(1, 25)
        f, checks, _ = brent_rho_factor(n, seed=seed, c=c, max_steps=25_000)
        total += checks

        if exact_factor(n, f):
            return f, total

    return None, total


def benchmark(n: int) -> Dict[str, Any]:
    sqi = sqi_factor_once(n)

    return {
        "n": n,
        "miller_rabin_probable_prime": miller_rabin_is_probable_prime(n),
        "naive": time_call(naive_trial_factor, n),
        "wheel": time_call(wheel_only_factor, n),
        "fermat_only": time_call(fermat_only_factor, n),
        "pollard_only": time_call(pollard_only_factor, n),
        "brent_only": time_call(brent_only_factor, n),
        "sqi": {
            "factor": sqi.found_factor,
            "cofactor": sqi.cofactor,
            "method": sqi.method,
            "checks": sqi.checked,
            "branches_generated": sqi.branches_generated,
            "branches_pruned": sqi.branches_pruned,
            "elapsed_ms": round(sqi.elapsed_ms, 4),
            "trace_path": sqi.trace_path,
            "dashboard_path": sqi.dashboard_path,
            "trace_tail": sqi.trace[-5:],
        },
        "full_factorization": sorted(factor_recursive(n)),
    }


LARGER_SEMIPRIME_CASES = [
    ("small_91", 91),
    ("small_8051", 83 * 97),
    ("close_5_digit", 10007 * 10009),
    ("close_8_digit", 10000019 * 10000169),
    ("spread_small_factor", 1000003 * 1009),
    ("spread_mid_factor", 104729 * 101),
    ("spread_6_digit_primes", 999983 * 1009),
    ("spread_7_digit_prime", 15485863 * 1009),
    ("less_close_1", 10007 * 20011),
    ("less_close_2", 1000003 * 1000033),
    ("medium_semiprime_1", 1000003 * 1000037),
    ("medium_semiprime_2", 1000033 * 1000037),
]


def run_large_benchmark_table() -> List[Dict[str, Any]]:
    results = []

    for name, n in LARGER_SEMIPRIME_CASES:
        out = benchmark(n)
        out["case"] = name
        results.append(out)

    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BENCHMARK_DIR / "sqi_prime_factor_benchmark_v2.json"
    out_path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")

    dashboard_rows = [
        {
            "case": row["case"],
            "n": row["n"],
            "sqi_method": row["sqi"]["method"],
            "sqi_ms": row["sqi"]["elapsed_ms"],
            "sqi_factor": row["sqi"]["factor"],
            "naive_ms": row["naive"]["elapsed_ms"],
            "wheel_ms": row["wheel"]["elapsed_ms"],
            "fermat_ms": row["fermat_only"]["elapsed_ms"],
            "pollard_ms": row["pollard_only"]["elapsed_ms"],
            "brent_ms": row["brent_only"]["elapsed_ms"],
        }
        for row in results
    ]

    dashboard_path = BENCHMARK_DIR / "sqi_prime_factor_dashboard_v2.json"
    dashboard_path.write_text(json.dumps(dashboard_rows, indent=2, sort_keys=True), encoding="utf-8")

    return results


if __name__ == "__main__":
    rows = run_large_benchmark_table()
    for row in rows:
        print("=" * 100)
        print(json.dumps({
            "case": row["case"],
            "n": row["n"],
            "sqi_method": row["sqi"]["method"],
            "sqi_ms": row["sqi"]["elapsed_ms"],
            "sqi_checks": row["sqi"]["checks"],
            "factor": row["sqi"]["factor"],
            "cofactor": row["sqi"]["cofactor"],
            "trace_path": row["sqi"]["trace_path"],
            "dashboard_path": row["sqi"]["dashboard_path"],
        }, indent=2))
    print("=" * 100)
    print("✅ wrote benchmarks/sqi_prime_factor_benchmark_v2.json")
    print("✅ wrote benchmarks/sqi_prime_factor_dashboard_v2.json")


def rho_seed_wave_search(
    n: int,
    *,
    seed_count: int = 128,
    max_steps_per_seed: int = 50_000,
    rng_seed: int = 424242,
    prefer: str = "brent",
    learned_seed_priors: Optional[List[Tuple[int, int]]] = None,
) -> Tuple[Optional[int], int, List[Dict[str, Any]]]:
    """
    SQI seed-wave search.

    Treats Pollard/Brent seed choices as a symbolic branch wave:
    each (seed, c) pair is a branch. The first branch that produces a
    verified non-trivial divisor collapses the wave.

    This is still classical arithmetic, but it is SQI-shaped:
    many symbolic branches, bounded branch work, verified collapse.
    """
    rng = Random(rng_seed)
    total_checked = 0
    trace: List[Dict[str, Any]] = []

    # Deterministic seed schedule: learned priors first, then low seeds,
    # then random seed branches.
    branches: List[Tuple[int, int]] = []

    for pair in learned_seed_priors or []:
        seed, c = pair
        if seed > 1 and c > 0 and (seed, c) not in branches:
            branches.append((seed, c))

    for i in range(min(seed_count, 32)):
        pair = (2 + i, 1 + (i % 23))
        if pair not in branches:
            branches.append(pair)

    while len(branches) < seed_count:
        seed = rng.randint(2, max(3, min(n - 2, 1_000_000)))
        c = rng.randint(1, 97)
        pair = (seed, c)
        if pair not in branches:
            branches.append(pair)

    for branch_i, (seed, c) in enumerate(branches):
        if prefer == "pollard":
            factor, checks, branch_trace = pollard_rho_factor(
                n,
                seed=seed,
                c=c,
                max_steps=max_steps_per_seed,
            )
            method = "pollard_rho_seed_wave"
        else:
            factor, checks, branch_trace = brent_rho_factor(
                n,
                seed=seed,
                c=c,
                max_steps=max_steps_per_seed,
            )
            method = "brent_rho_seed_wave"

        total_checked += checks

        trace.append({
            "event": "seed_wave_branch",
            "branch": branch_i,
            "method": method,
            "seed": seed,
            "c": c,
            "checks": checks,
            "found": factor,
            "trace_tail": branch_trace[-3:],
        })

        if exact_factor(n, factor):
            trace.append({
                "event": "seed_wave_collapse",
                "branch": branch_i,
                "method": method,
                "seed": seed,
                "c": c,
                "factor": factor,
                "cofactor": n // factor,
                "total_checked": total_checked,
            })
            return factor, total_checked, trace

    return None, total_checked, trace[-20:]


def adaptive_seed_wave_ladder(
    n: int,
    *,
    learned_seed_priors: Optional[List[Tuple[int, int]]] = None,
    rng_seed: int = 999_001,
) -> Tuple[Optional[int], int, List[Dict[str, Any]], str]:
    """
    Adaptive SQI seed-wave escalation ladder.

    Attempts increasingly broad/deep Rho/Brent seed waves.
    Returns:
      factor, total_checks, trace, method_name
    """
    total_checked = 0
    trace: List[Dict[str, Any]] = []

    stages = [
        {
            "stage": "learned_brent_priors",
            "prefer": "brent",
            "seed_count": max(32, len(learned_seed_priors or [])),
            "max_steps": 100_000,
            "priors": learned_seed_priors or [],
        },
        {
            "stage": "deterministic_low_brent",
            "prefer": "brent",
            "seed_count": 128,
            "max_steps": 100_000,
            "priors": [],
        },
        {
            "stage": "wide_random_brent",
            "prefer": "brent",
            "seed_count": 256,
            "max_steps": 150_000,
            "priors": learned_seed_priors or [],
        },
        {
            "stage": "wide_random_pollard",
            "prefer": "pollard",
            "seed_count": 256,
            "max_steps": 150_000,
            "priors": learned_seed_priors or [],
        },
        {
            "stage": "deep_brent",
            "prefer": "brent",
            "seed_count": 512,
            "max_steps": 250_000,
            "priors": learned_seed_priors or [],
        },
    ]

    for stage_i, stage in enumerate(stages):
        stage_seed = rng_seed + (stage_i * 100_003)

        trace.append({
            "event": "ladder_stage_start",
            "stage": stage["stage"],
            "prefer": stage["prefer"],
            "seed_count": stage["seed_count"],
            "max_steps": stage["max_steps"],
            "prior_count": len(stage["priors"]),
        })

        factor, checks, stage_trace = rho_seed_wave_search(
            n,
            seed_count=stage["seed_count"],
            max_steps_per_seed=stage["max_steps"],
            rng_seed=stage_seed,
            prefer=stage["prefer"],
            learned_seed_priors=stage["priors"],
        )

        total_checked += checks
        trace.extend(stage_trace[-25:])

        if exact_factor(n, factor):
            method_name = f"{stage['prefer']}_rho_seed_wave_ladder_{stage['stage']}"
            trace.append({
                "event": "ladder_collapse",
                "stage": stage["stage"],
                "method": method_name,
                "factor": factor,
                "cofactor": n // factor,
                "total_checked": total_checked,
            })
            return factor, total_checked, trace, method_name

        trace.append({
            "event": "ladder_stage_miss",
            "stage": stage["stage"],
            "checked": checks,
            "total_checked": total_checked,
        })

    return None, total_checked, trace, "adaptive_seed_wave_ladder_none"
