from backend.modules.aion_business.runtime.desktop_custody_attestation import (
    desktop_custody_attestation,
)


def test_desktop_custody_attestation_binds_guardian_without_exposing_identity() -> None:
    stable_id = "business-12345678"
    result = desktop_custody_attestation({
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_STABLE_ID": stable_id,
    })

    assert result["mode"] == "guardian"
    assert len(result["business_stable_id_sha256"]) == 64
    assert stable_id not in repr(result)


def test_desktop_custody_attestation_is_not_guardian_without_authority() -> None:
    result = desktop_custody_attestation({})

    assert result["mode"] == ""
    assert result["business_stable_id_sha256"] == ""
