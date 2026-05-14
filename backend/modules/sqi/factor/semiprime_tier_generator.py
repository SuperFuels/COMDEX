from __future__ import annotations

import argparse
import json
import random
from math import prod
from pathlib import Path
from typing import Dict, Any


_SMALL_PRIMES = [
    3, 5, 7, 11, 13, 17, 19, 23, 29, 31,
    37, 41, 43, 47, 53, 59, 61, 67, 71, 73,
]


def is_probable_prime(n: int, rounds: int = 16) -> bool:
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False

    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2

    # deterministic enough for this lab scale + extra random rounds
    bases = [2, 3, 5, 7, 11, 13, 17, 19]
    rng = random.Random(n ^ 0xA10F)
    while len(bases) < rounds:
        bases.append(rng.randrange(2, n - 2))

    for a in bases[:rounds]:
        if a % n == 0:
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        ok = False
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                ok = True
                break
        if not ok:
            return False
    return True


def random_prime(bits: int, rng: random.Random) -> int:
    assert bits >= 8
    while True:
        n = rng.getrandbits(bits)
        n |= (1 << (bits - 1))
        n |= 1
        if is_probable_prime(n):
            return n


def generate_semiprime(p_bits: int, q_bits: int, seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    p = random_prime(p_bits, rng)
    q = random_prime(q_bits, rng)
    if p > q:
        p, q = q, p
    n = p * q
    return {
        "p_bits": p_bits,
        "q_bits": q_bits,
        "n_bits": n.bit_length(),
        "seed": seed,
        "p": p,
        "q": q,
        "n": n,
        "verified": p * q == n,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--p-bits", type=int, required=True)
    ap.add_argument("--q-bits", type=int, required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    payload = generate_semiprime(args.p_bits, args.q_bits, args.seed)

    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
