from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.modules.aion_business.runtime.legal_signing_service import (
    LegalSigningError,
    LegalSigningService,
)
from backend.modules.aion_business.runtime.public_signer_rate_limit import PublicSignerRateLimiter
from backend.modules.aion_business.runtime.legal_template_service import (
    LegalTemplateError,
    LegalTemplateService,
)


def _issued(service: LegalSigningService) -> str:
    envelope = service.create_envelope(
        "workspace-a",
        title="Bounded public signing",
        document_content="Exact agreement text",
        signers=[{"name": "A Person", "email": "a@example.com"}],
        actor_id="owner-1",
    )
    pending = service.submit_for_approval("workspace-a", envelope["envelope_id"], "owner-1")
    service.approve(
        "workspace-a", envelope["envelope_id"], "owner-1",
        pending["approval"]["review_hash"],
    )
    return service.issue("workspace-a", envelope["envelope_id"], "owner-1")["secure_links"][0]["token"]


def test_public_signer_lookup_uses_encrypted_constant_time_index(tmp_path):
    service = LegalSigningService(
        root=tmp_path / "signing",
        clock=lambda: datetime(2026, 9, 26, tzinfo=timezone.utc),
    )
    token = _issued(service)
    token_hash = service._find_by_token(token)[1]["token_hash"]
    index = service.token_index_root / f"{token_hash}.enc"
    assert index.exists()
    assert token.encode("utf-8") not in index.read_bytes()

    # Once migrated, a well-formed random token is rejected without scanning
    # or decrypting every workspace record.
    service._token_index_marker().write_text("complete\n", encoding="utf-8")
    service._read = lambda _path: pytest.fail("random misses must not scan records")
    with pytest.raises(LegalSigningError, match="secure_signing_link_invalid"):
        service.signer_view("A" * 43)


def test_public_signer_index_is_removed_when_token_is_consumed(tmp_path):
    service = LegalSigningService(
        root=tmp_path / "signing",
        clock=lambda: datetime(2026, 9, 26, tzinfo=timezone.utc),
    )
    token = _issued(service)
    token_hash = service._find_by_token(token)[1]["token_hash"]
    index = service.token_index_root / f"{token_hash}.enc"
    service.sign(token, "A Person", "a@example.com")
    assert not index.exists()
    with pytest.raises(LegalSigningError, match="secure_signing_link_invalid"):
        service.signer_view(token)


def test_public_signer_limiter_is_bounded_and_separates_read_from_write():
    now = [100.0]
    limiter = PublicSignerRateLimiter(
        clock=lambda: now[0], window_seconds=60,
        read_per_source=2, read_per_token=2,
        write_per_source=1, write_per_token=1,
        max_buckets=256,
    )
    assert limiter.allow(source="client-a", token="A" * 43, write=False)[0]
    assert limiter.allow(source="client-a", token="A" * 43, write=False)[0]
    allowed, retry = limiter.allow(source="client-a", token="A" * 43, write=False)
    assert allowed is False and retry > 0
    assert limiter.allow(source="client-a", token="A" * 43, write=True)[0]
    assert limiter.allow(source="client-a", token="A" * 43, write=True)[0] is False

    for index in range(400):
        limiter.allow(source=f"source-{index}", token=("B" * 40) + f"{index:03d}", write=False)
    assert limiter.bucket_count <= 256

    now[0] += 61
    assert limiter.allow(source="client-a", token="A" * 43, write=True)[0]


def test_legal_template_substitution_is_bounded(tmp_path):
    service = LegalTemplateService(root=tmp_path / "templates")
    service.MAX_VARIABLES = 2
    with pytest.raises(LegalTemplateError, match="template_variable_limit_exceeded"):
        service.create_draft(
            "workspace-a", title="Too many variables", template_type="OTHER",
            jurisdiction={"country_code": "IE", "governing_law": "Irish law"},
            content="{{ONE}} {{TWO}} {{THREE}}", intended_use="test", actor_id="owner-1",
        )

    draft = service.create_draft(
        "workspace-a", title="Bounded variables", template_type="OTHER",
        jurisdiction={"country_code": "IE", "governing_law": "Irish law"},
        content="Hello {{NAME}}", intended_use="test", actor_id="owner-1",
    )
    approved = service.approve(
        "workspace-a", draft["template_id"], actor_id="owner-1",
        expected_content_sha256=draft["content_sha256"], reviewer_name="Reviewer",
        reviewer_qualification="Qualified reviewer", review_scope="Exact test wording",
        approved_jurisdiction="Ireland", acknowledge_qualified_review=True,
    )
    service.MAX_VALUE_CHARS = 4
    with pytest.raises(LegalTemplateError, match="template_variable_value_too_large"):
        service.instantiate(
            "workspace-a", approved["template_id"], actor_id="owner-1",
            values={"NAME": "12345"},
        )
