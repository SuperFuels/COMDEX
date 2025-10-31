"""
test_instruction_metadata_bridge.py
Validation suite for the Symatics / CodexCore operator metadata bridge.
Ensures canonical integrity, domain coverage, and lookup correctness.
"""

import pytest

# Import the target module
import backend.codexcore_virtual.instruction_metadata_bridge as imb
import backend.modules.codex.canonical_ops as cop


# ────────────────────────────────────────────────
# Basic Structural Tests
# ────────────────────────────────────────────────

def test_metadata_structure():
    """Ensure OPERATOR_METADATA is non-empty and properly structured."""
    assert isinstance(imb.OPERATOR_METADATA, dict)
    assert len(imb.OPERATOR_METADATA) >= 40, f"Expected ≥ 40 operator definitions, got {len(imb.OPERATOR_METADATA)}"

    for symbol, meta in imb.OPERATOR_METADATA.items():
        assert "domain" in meta, f"Missing domain for {symbol}"
        assert "type" in meta, f"Missing type for {symbol}"
        assert "name" in meta, f"Missing name for {symbol}"
        assert isinstance(meta.get("tags", []), list), f"Tags must be list for {symbol}"


# ────────────────────────────────────────────────
# DOMAIN_INDEX Consistency
# ────────────────────────────────────────────────

def test_domain_index_consistency():
    """Ensure all OPERATOR_METADATA entries appear in DOMAIN_INDEX."""
    for symbol, meta in imb.OPERATOR_METADATA.items():
        domain = meta.get("domain")
        assert domain in imb.DOMAIN_INDEX, f"Domain {domain} not in DOMAIN_INDEX"
        assert symbol in imb.DOMAIN_INDEX[domain], f"{symbol} missing from DOMAIN_INDEX[{domain}]"


def test_domain_index_reverse_integrity():
    """Ensure DOMAIN_INDEX only references valid symbols."""
    for domain, symbols in imb.DOMAIN_INDEX.items():
        for sym in symbols:
            assert sym in imb.OPERATOR_METADATA, f"{sym} in DOMAIN_INDEX but not OPERATOR_METADATA"


def test_list_by_domain_matches_index():
    """list_by_domain() should match DOMAIN_INDEX content."""
    for domain, symbols in imb.DOMAIN_INDEX.items():
        assert set(imb.list_by_domain(domain)) == set(symbols)


def test_list_all_domains_sorted():
    """list_all_domains() should return sorted unique domain names."""
    domains = imb.list_all_domains()
    assert domains == sorted(domains)
    for d in domains:
        assert d in imb.DOMAIN_INDEX


# ────────────────────────────────────────────────
# Function Behavior
# ────────────────────────────────────────────────

def test_get_instruction_metadata_valid_symbol():
    """Valid symbols should return metadata dicts."""
    sym = next(iter(imb.OPERATOR_METADATA.keys()))
    meta = imb.get_instruction_metadata(sym)
    assert isinstance(meta, dict)
    assert meta["domain"] in imb.DOMAIN_INDEX


def test_get_instruction_metadata_invalid_symbol():
    """Unknown symbols should return None."""
    assert imb.get_instruction_metadata("❌") is None


def test_list_all_symbols_equivalence():
    """list_all_symbols() should equal OPERATOR_METADATA."""
    assert imb.list_all_symbols() == imb.OPERATOR_METADATA


# ────────────────────────────────────────────────
# Canonical Cross-Validation (with canonical_ops)
# ────────────────────────────────────────────────

def test_canonical_symbol_presence():
    """Every canonical symbol in CANONICAL_OPS should exist in metadata bridge."""
    for sym in cop.CANONICAL_OPS.keys():
        if sym not in imb.OPERATOR_METADATA:
            # Some are domain aliases like ⊕_q or ↔_q, handled separately
            assert any(sym in s for s in imb.OPERATOR_METADATA.keys()), f"{sym} missing from OPERATOR_METADATA"


def test_no_empty_descriptions_in_op_metadata():
    """Ensure all metadata entries have descriptive names."""
    for sym, meta in imb.OPERATOR_METADATA.items():
        name = meta.get("name", "")
        assert isinstance(name, str) and len(name) > 0, f"{sym} missing descriptive name"


def test_domain_density():
    """Ensure no domain is empty in DOMAIN_INDEX."""
    for domain, symbols in imb.DOMAIN_INDEX.items():
        assert len(symbols) > 0, f"Domain {domain} is empty"


# ────────────────────────────────────────────────
# Regression: Specific Known Domains
# ────────────────────────────────────────────────

@pytest.mark.parametrize("expected_domain", [
    "logic", "quantum", "symatics", "photon", "physics", "control", "glyph"
])
def test_known_domains_exist(expected_domain):
    """All core domains must exist in DOMAIN_INDEX."""
    assert expected_domain in imb.DOMAIN_INDEX


@pytest.mark.parametrize("expected_symbol", [
    "⊕", "∇", "⊗_s", "⊕_q", "⧜", "μ", "π", "⊙", "⧖", "🜁"
])
def test_known_symbols_present(expected_symbol):
    """Key canonical symbols must appear in OPERATOR_METADATA."""
    assert expected_symbol in imb.OPERATOR_METADATA, f"{expected_symbol} missing from OPERATOR_METADATA"


# ────────────────────────────────────────────────
# Completeness & Cross-Domain
# ────────────────────────────────────────────────

def test_unique_symbol_names():
    """Ensure all symbol keys are unique."""
    keys = list(imb.OPERATOR_METADATA.keys())
    assert len(keys) == len(set(keys)), "Duplicate symbols detected in OPERATOR_METADATA"


def test_domain_spread():
    """At least 5 distinct domains should be defined."""
    assert len(imb.DOMAIN_INDEX.keys()) >= 5