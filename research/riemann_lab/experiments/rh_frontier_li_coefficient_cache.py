#!/usr/bin/env python3
"""Persistent, extendable Arb cache for full Li coefficient construction."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

from flint import acb, arb, ctx


CACHE_FORMAT = "aion_full_li_taylor_cache_v1"


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def read_json(path: Path) -> dict:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        if path.suffix == ".gz":
            with os.fdopen(descriptor, "wb") as raw:
                with gzip.open(raw, "wt", encoding="utf-8", compresslevel=6) as handle:
                    json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
                    handle.write("\n")
                raw.flush()
                os.fsync(raw.fileno())
        else:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        Path(temporary_name).replace(path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def empty_cache(digits: int) -> dict:
    return {
        "format": CACHE_FORMAT,
        "digits": digits,
        "count": 0,
        "regularized_zeta": [str(arb(1))],
        "log_regularized_zeta": [str(arb(0))],
        "log_xi_taylor": [str(arb(0))],
        "li_coefficients": [str(arb(0))],
        "claim_boundary": "Finite coefficient cache only; not an RH proof.",
    }


def verify_cache(payload: dict, digits: int) -> None:
    if payload.get("format") != CACHE_FORMAT:
        raise ValueError("unsupported Li coefficient cache format")
    saved_hash = payload.get("cache_sha256")
    core = {key: value for key, value in payload.items() if key != "cache_sha256"}
    if saved_hash != canonical_hash(core):
        raise ValueError("Li coefficient cache hash mismatch")
    if payload["digits"] != digits:
        raise ValueError(
            "cache precision differs from requested precision; rebuild rather than promote intervals"
        )
    expected = payload["count"] + 1
    for key in (
        "regularized_zeta", "log_regularized_zeta", "log_xi_taylor", "li_coefficients"
    ):
        if len(payload[key]) != expected:
            raise ValueError(f"cache array length mismatch for {key}")


def bootstrap_cache_from_rover_state(
    state_path: Path, cache_path: Path, digits: int
) -> dict:
    """Invert the Li binomial transform and reconstruct the Taylor cache."""
    ctx.dps = digits
    state = read_json(state_path)
    state_hash = state.get("state_sha256")
    state_core = {key: value for key, value in state.items() if key != "state_sha256"}
    if state_hash != canonical_hash(state_core):
        raise ValueError("source rover state hash mismatch")
    if state["digits"] != digits:
        raise ValueError("source rover state precision mismatch")
    count = state["completed_order"]
    li = [arb(value) for value in state["coefficients"]]
    if len(li) != count + 1:
        raise ValueError("source rover coefficient length mismatch")

    euler = arb.const_euler()
    log2 = arb.const_log2()
    pi = arb.const_sqrt_pi() ** 2
    logpi = pi.log()
    log_xi = [arb(0) for _ in range(count + 1)]
    log_regularized = [arb(0) for _ in range(count + 1)]
    regularized = [arb(0) for _ in range(count + 1)]
    regularized[0] = arb(1)

    # Invert lambda_n/n = sum_k binom(n-1,k-1) a_k.
    for n in range(1, count + 1):
        log_xi[n] = sum(
            (
                arb(1 if (n - k) % 2 == 0 else -1)
                * math.comb(n - 1, k - 1)
                * li[k]
                / k
                for k in range(1, n + 1)
            ),
            arb(0),
        )
        log_one_plus = arb(1 if n % 2 else -1) / n
        if n == 1:
            log_gamma = (-euler - 2 * log2) / 2
            archimedean_linear = -logpi / 2
        else:
            log_gamma = (
                arb(1 if n % 2 == 0 else -1)
                * ((arb(2) ** n) - 1)
                * arb(n).zeta()
                / (n * (arb(2) ** n))
            )
            archimedean_linear = arb(0)
        log_regularized[n] = (
            log_xi[n] - log_one_plus - archimedean_linear - log_gamma
        )
        correction = sum(
            (k * log_regularized[k] * regularized[n - k] for k in range(1, n)),
            arb(0),
        )
        regularized[n] = log_regularized[n] + correction / n

    check_degrees = sorted({1, max(1, count // 2), count})
    checks = []
    for degree in check_degrees:
        gamma = acb.stieltjes(degree - 1)
        direct = gamma.real / math.factorial(degree - 1)
        if degree % 2 == 0:
            direct = -direct
        overlap = not bool(regularized[degree].upper() < direct.lower()) and not bool(
            direct.upper() < regularized[degree].lower()
        )
        checks.append({"degree": degree, "overlap": overlap})
    if not all(check["overlap"] for check in checks):
        raise ArithmeticError("bootstrapped Taylor cache failed Stieltjes spot checks")

    core = {
        "format": CACHE_FORMAT,
        "digits": digits,
        "count": count,
        "regularized_zeta": [str(value) for value in regularized],
        "log_regularized_zeta": [str(value) for value in log_regularized],
        "log_xi_taylor": [str(value) for value in log_xi],
        "li_coefficients": [str(value) for value in li],
        "claim_boundary": "Finite coefficient cache only; not an RH proof.",
        "bootstrap": {
            "source_state": str(state_path),
            "source_state_sha256": state_hash,
            "stieltjes_spot_checks": checks,
        },
    }
    payload = {**core, "cache_sha256": canonical_hash(core)}
    save_json_atomic(cache_path, payload)
    return payload


def extend_cache(path: Path, target: int, digits: int) -> tuple[dict, list[arb]]:
    if target < 0 or digits < 50:
        raise ValueError("invalid target or precision")
    ctx.dps = digits
    if path.exists():
        payload = read_json(path)
        verify_cache(payload, digits)
        start = payload["count"]
    else:
        payload = empty_cache(digits)
        start = 0

    regularized = [arb(value) for value in payload["regularized_zeta"]]
    log_regularized = [arb(value) for value in payload["log_regularized_zeta"]]
    log_xi = [arb(value) for value in payload["log_xi_taylor"]]
    li = [arb(value) for value in payload["li_coefficients"]]

    if target < start:
        return payload, li[: target + 1]

    euler = arb.const_euler()
    log2 = arb.const_log2()
    pi = arb.const_sqrt_pi() ** 2
    logpi = pi.log()
    for degree in range(start + 1, target + 1):
        gamma = acb.stieltjes(degree - 1)
        if gamma.imag != 0:
            raise ArithmeticError("Stieltjes enclosure unexpectedly nonreal")
        coefficient = gamma.real / math.factorial(degree - 1)
        zeta_coefficient = coefficient if degree % 2 else -coefficient
        regularized.append(zeta_coefficient)

        correction = sum(
            (k * log_regularized[k] * regularized[degree - k]
             for k in range(1, degree)),
            arb(0),
        )
        log_regularized.append(regularized[degree] - correction / degree)

        log_one_plus = arb(1 if degree % 2 else -1) / degree
        if degree == 1:
            log_gamma = (-euler - 2 * log2) / 2
            archimedean_linear = -logpi / 2
        else:
            log_gamma = (
                arb(1 if degree % 2 == 0 else -1)
                * ((arb(2) ** degree) - 1)
                * arb(degree).zeta()
                / (degree * (arb(2) ** degree))
            )
            archimedean_linear = arb(0)
        log_xi.append(
            log_one_plus + archimedean_linear + log_gamma + log_regularized[degree]
        )

        transformed = sum(
            (math.comb(degree - 1, k - 1) * log_xi[k]
             for k in range(1, degree + 1)),
            arb(0),
        )
        li.append(degree * transformed)

    core = {
        "format": CACHE_FORMAT,
        "digits": digits,
        "count": target,
        "regularized_zeta": [str(value) for value in regularized[: target + 1]],
        "log_regularized_zeta": [str(value) for value in log_regularized[: target + 1]],
        "log_xi_taylor": [str(value) for value in log_xi[: target + 1]],
        "li_coefficients": [str(value) for value in li[: target + 1]],
        "claim_boundary": "Finite coefficient cache only; not an RH proof.",
    }
    payload = {**core, "cache_sha256": canonical_hash(core)}
    save_json_atomic(path, payload)
    return payload, li[: target + 1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--target", type=int, required=True)
    parser.add_argument("--digits", type=int, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--bootstrap-state", type=Path)
    args = parser.parse_args()
    if args.bootstrap_state:
        if args.cache.exists():
            raise SystemExit("refusing to overwrite an existing cache during bootstrap")
        bootstrap_cache_from_rover_state(args.bootstrap_state, args.cache, args.digits)
    previous = read_json(args.cache)["count"] if args.cache.exists() else 0
    payload, coefficients = extend_cache(args.cache, args.target, args.digits)
    summary = {
        "experiment": "extendable_full_li_coefficient_cache",
        "digits": args.digits,
        "starting_count": previous,
        "completed_count": payload["count"],
        "new_coefficients": max(0, payload["count"] - previous),
        "cache_sha256": payload["cache_sha256"],
        "last_li_coefficient": str(coefficients[-1]),
        "claim_boundary": "Finite coefficient construction only; not an RH proof.",
    }
    summary["payload_sha256"] = canonical_hash(summary)
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.summary:
        save_json_atomic(args.summary, summary)
    print(rendered, end="")


if __name__ == "__main__":
    main()
