from pathlib import Path

from backend.modules.sqi.factor.semiprime_lab import (
    build_cases,
    generate_probable_prime,
    make_proof_certificate,
    run_lab,
    run_case,
)
from random import Random


def test_generate_probable_prime():
    rng = Random(123)
    p = generate_probable_prime(20, rng)
    assert p.bit_length() == 20


def test_proof_certificate_verified():
    cert = make_proof_certificate(91, 7, 13)
    assert cert.verified
    assert cert.probable_prime_factor
    assert cert.probable_prime_cofactor


def test_run_single_case():
    cases = build_cases(
        seed=123,
        close_bits=[16],
        spread_pairs=[],
        per_tier=1,
    )
    result = run_case(cases[0], trace=False, dashboard=False)
    assert result.proof.verified
    assert result.sqi["factor"] * result.sqi["cofactor"] == result.case.n


def test_run_lab_writes_report():
    payload = run_lab(
        seed=123,
        close_bits=[16],
        spread_pairs=[(12, 20)],
        per_tier=1,
        trace=False,
        dashboard=False,
    )
    assert payload["summary"]["total_cases"] == 2
    assert payload["summary"]["sqi_solved"] == 2
    assert Path("benchmarks/sqi_semiprime_lab/semiprime_lab_report.json").exists()
    assert Path("benchmarks/sqi_semiprime_lab/semiprime_lab_summary.json").exists()


def test_method_family_accepts_seed_wave_learned_first():
    from backend.modules.sqi.factor.semiprime_lab import method_family

    assert method_family("brent_rho_seed_wave_learned_first") == "spread"
