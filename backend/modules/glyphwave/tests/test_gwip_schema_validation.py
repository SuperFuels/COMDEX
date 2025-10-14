"""
✅ GWIP Schema Validation Tests (SRK-9)
Ensures structural + semantic integrity of GWIP packets via:
 - JSON Schema validation (gwip_packet_schema.json)
 - Pydantic metadata validation (GWIPMetadata)
"""

import pytest
import jsonschema
from backend.modules.glyphwave.protocol.gwip_schema import (
    validate_gwip_schema,
    validate_gwip_packet,
    GWIPMetadata,
)
from backend.modules.glyphwave.carrier.carrier_types import CarrierType


# ────────────────────────────────────────────────────────────────
# 🧩 Fixtures
# ----------------------------------------------------------------
@pytest.fixture
def valid_gwip_packet():
    """Minimal valid GWIP packet that satisfies schema + metadata model."""
    return {
        "type": "gwip",
        "schema": 2,
        "envelope": {
            "packet_id": "gwip_0001",
            "source_container": "beam_alpha",
            "target_container": "beam_beta",
            "carrier_type": CarrierType.SIMULATED.name,
            "freq": 2.45e9,
            "phase": 0.5,
            "coherence": 0.97,
            "timestamp": 173947.4,
        },
        "payload": "ab12cd34ef",
        # ✅ Updated to 128 hex chars (valid SHA3-512 pattern)
        "hash": "deadbeef" * 16,
        "signature": "sig_xyz_123",
    }


@pytest.fixture
def invalid_gwip_packet_missing_field(valid_gwip_packet):
    """Packet missing mandatory envelope field."""
    broken = valid_gwip_packet.copy()
    broken["envelope"] = broken["envelope"].copy()
    del broken["envelope"]["packet_id"]
    return broken


@pytest.fixture
def invalid_gwip_packet_wrong_type(valid_gwip_packet):
    """Packet with wrong field type (freq as string)."""
    broken = valid_gwip_packet.copy()
    broken["envelope"] = broken["envelope"].copy()
    broken["envelope"]["freq"] = "not_a_number"
    return broken


# ────────────────────────────────────────────────────────────────
# ✅ Tests: JSON Schema validation
# ----------------------------------------------------------------
def test_schema_validation_passes(valid_gwip_packet):
    """Ensure a valid GWIP passes JSON schema validation."""
    try:
        validate_gwip_schema(valid_gwip_packet)
    except Exception as e:
        pytest.fail(f"Unexpected schema validation failure: {e}")


def test_schema_validation_fails_missing_field(invalid_gwip_packet_missing_field):
    """Schema should fail if a required field is missing."""
    with pytest.raises(jsonschema.ValidationError):
        validate_gwip_schema(invalid_gwip_packet_missing_field)


def test_schema_validation_fails_wrong_type(invalid_gwip_packet_wrong_type):
    """Schema should fail if a field type is incorrect."""
    with pytest.raises(jsonschema.ValidationError):
        validate_gwip_schema(invalid_gwip_packet_wrong_type)


# ────────────────────────────────────────────────────────────────
# ✅ Tests: Combined JSON + Pydantic validation
# ----------------------------------------------------------------
def test_combined_validation_returns_metadata(valid_gwip_packet):
    """Dual-layer validation should return a proper GWIPMetadata object."""
    meta = validate_gwip_packet(valid_gwip_packet)
    assert isinstance(meta, GWIPMetadata)
    assert meta.packet_id == "gwip_0001"
    assert meta.carrier_type == CarrierType.SIMULATED


def test_combined_validation_detects_invalid_field(valid_gwip_packet):
    """Coherence > 1.0 should trigger Pydantic validation error."""
    gwip = valid_gwip_packet.copy()
    gwip["envelope"] = gwip["envelope"].copy()
    gwip["envelope"]["coherence"] = 1.5
    with pytest.raises(Exception):
        validate_gwip_packet(gwip)


# ────────────────────────────────────────────────────────────────
# 🧠 Smoke test: schema file availability
# ----------------------------------------------------------------
def test_schema_file_exists():
    """Ensure the schema file is present and readable."""
    from pathlib import Path
    from backend.modules.glyphwave.protocol import gwip_schema
    assert Path(gwip_schema.SCHEMA_PATH).exists(), "gwip_packet_schema.json not found"