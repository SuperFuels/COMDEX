"""Small real-work callables used by the multi-surface Vault qualification campaign.

These functions deliberately contain no release-pass assertions.  The discovery
runner observes their actual destinations and the aggregate gate decides whether
the complete journey is safe.
"""

from __future__ import annotations

import os
from pathlib import Path

from backend.modules.aion_business.runtime.finance_inbox_service import FinanceInboxService
from backend.modules.aion_business.runtime.legal_document_service import LegalDocumentService
from backend.modules.aion_business.runtime.legal_template_service import LegalTemplateService
from backend.modules.aion_business.runtime.organization_authority_service import (
    OrganizationAuthorityService,
)
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)


def import_finance_evidence() -> None:
    source = Path(os.environ["TESSARIS_DISCOVERY_FINANCE_IMPORT_PATH"]).resolve(strict=True)
    workspace_id = os.environ["TESSARIS_DISCOVERY_WORKSPACE_ID"]
    content = source.read_bytes()
    actor_id = os.environ.get("TESSARIS_DISCOVERY_ACTOR_ID") or "discovery-import"
    FinanceInboxService().ingest(
        workspace_id,
        filename=source.name,
        content=content,
        mime_type="text/csv",
        channel="filesystem_import",
        document_type="other",
        submitted_by_person_id=actor_id,
        source_reference="filesystem-import-qualification-direct",
    )


def import_support_legal_evidence() -> None:
    """Retain a legal original, local review and exact approved template.

    The source original enters the Business Vault File Cabinet.  Legal working
    records remain encrypted under the explicitly configured external secret
    store so their storage and signing keys cannot be overwritten by an app
    update and cannot be mistaken for ordinary application files.
    """
    source = Path(os.environ["TESSARIS_DISCOVERY_LEGAL_IMPORT_PATH"]).resolve(strict=True)
    legal_root = Path(os.environ["TESSARIS_DISCOVERY_LEGAL_ROOT"]).resolve(strict=False)
    workspace_id = os.environ["TESSARIS_DISCOVERY_WORKSPACE_ID"]
    actor_id = os.environ.get("TESSARIS_DISCOVERY_ACTOR_ID") or "discovery-import"
    content = source.read_bytes()

    WorkflowFileCabinetRepository.add_artifact(
        workspace_id,
        data=content,
        original_name=source.name,
        content_type="text/plain",
        display_name="Support contract evidence",
        document_type="legal_original",
        actor_id=actor_id,
    )

    documents = LegalDocumentService(root=legal_root / "documents")
    document = documents.ingest(
        workspace_id,
        filename=source.name,
        media_type="text/plain",
        content=content,
        actor_id=actor_id,
    )
    documents.confirm_classification(
        workspace_id, document["document_id"], actor_id=actor_id, category="CONTRACT"
    )
    documents.review_contract(workspace_id, document["document_id"], actor_id=actor_id)

    templates = LegalTemplateService(root=legal_root / "templates")
    template = templates.create_draft(
        workspace_id,
        title="Support service variation",
        template_type="CUSTOMER_AGREEMENT",
        jurisdiction={
            "country_code": "IE", "region": "",
            "governing_law": "Laws of Ireland", "owner_confirmed": True,
        },
        content=(
            "Service variation for {{CUSTOMER_NAME}}. The parties agree the reviewed scope. "
            "Governing law: Ireland. Personal data duties remain subject to approved policy."
        ),
        intended_use="Controlled support-case variation after qualified human review",
        actor_id=actor_id,
    )
    templates.approve(
        workspace_id,
        template["template_id"],
        actor_id=actor_id,
        expected_content_sha256=template["content_sha256"],
        reviewer_name="Qualification reviewer",
        reviewer_qualification="Authorised legal-content reviewer",
        review_scope="Exact template wording and stated jurisdiction",
        approved_jurisdiction="Ireland",
        acknowledge_qualified_review=True,
        review_interval_days=365,
    )

    OrganizationAuthorityService().record_policy_acknowledgement(
        workspace_id,
        person_id=actor_id,
        policy_id="legal-document-handling",
        policy_version="journey-20-v1",
        acknowledged_by=actor_id,
    )
