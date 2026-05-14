from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from time import perf_counter
from typing import Optional


@dataclass(frozen=True)
class FactorBeamResult:
    beam_id: str
    method: str
    factor: Optional[int]
    cofactor: Optional[int]
    checks: int
    elapsed_ms: float
    verified: bool
    seed: Optional[int] = None
    c: Optional[int] = None


def _verify(n: int, factor: Optional[int]) -> tuple[Optional[int], bool]:
    if factor is None or factor in (1, n):
        return None, False
    if n % factor != 0:
        return None, False
    return n // factor, True


def brent_factor_seeded(n: int, *, seed: int, c: int, max_steps: int) -> tuple[Optional[int], int]:
    if n % 2 == 0:
        return 2, 1

    y = seed % n
    c = c % n
    m = 128
    g = 1
    r = 1
    q = 1
    checks = 0

    while g == 1 and checks < max_steps:
        x = y
        for _ in range(r):
            y = (y * y + c) % n

        k = 0
        while k < r and g == 1 and checks < max_steps:
            ys = y
            for _ in range(min(m, r - k)):
                y = (y * y + c) % n
                q = (q * abs(x - y)) % n
                checks += 1
                if checks >= max_steps:
                    break
            g = gcd(q, n)
            k += m

        r *= 2

    if g == n:
        g = 1
        while g == 1 and checks < max_steps:
            ys = (ys * ys + c) % n
            g = gcd(abs(x - ys), n)
            checks += 1

    if 1 < g < n:
        return g, checks

    return None, checks


def pollard_factor_seeded(n: int, *, seed: int, c: int, max_steps: int) -> tuple[Optional[int], int]:
    if n % 2 == 0:
        return 2, 1

    x = seed % n
    y = x
    c = c % n

    for step in range(1, max_steps + 1):
        x = (x * x + c) % n
        y = (y * y + c) % n
        y = (y * y + c) % n
        g = gcd(abs(x - y), n)
        if 1 < g < n:
            return g, step
        if g == n:
            return None, step

    return None, max_steps


def run_factor_beam(
    *,
    n: int,
    beam_id: str,
    seeds: list[tuple[int, int]],
    prefer: str,
    max_steps: int,
) -> FactorBeamResult:
    start = perf_counter()
    total_checks = 0

    method_name = "parallel_qwave_brent" if prefer == "brent" else "parallel_qwave_pollard"

    for seed, c in seeds:
        if prefer == "brent":
            factor, checks = brent_factor_seeded(n, seed=seed, c=c, max_steps=max_steps)
        else:
            factor, checks = pollard_factor_seeded(n, seed=seed, c=c, max_steps=max_steps)

        total_checks += checks
        cofactor, verified = _verify(n, factor)

        if verified:
            return FactorBeamResult(
                beam_id=beam_id,
                method=method_name,
                factor=factor,
                cofactor=cofactor,
                checks=total_checks,
                elapsed_ms=round((perf_counter() - start) * 1000, 6),
                verified=True,
                seed=seed,
                c=c,
            )

    return FactorBeamResult(
        beam_id=beam_id,
        method=method_name,
        factor=None,
        cofactor=None,
        checks=total_checks,
        elapsed_ms=round((perf_counter() - start) * 1000, 6),
        verified=False,
    )
