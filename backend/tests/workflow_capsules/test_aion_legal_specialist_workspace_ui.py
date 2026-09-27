from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
LEGAL = (ROOT / "desktop/mac/src/aion_legal_workspace.js").read_text(encoding="utf-8")
INDEX = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
GATEWAY = (ROOT / "backend/modules/pilot_unified/workspace_gateway.py").read_text(encoding="utf-8")


def test_legal_specialist_is_a_connected_routable_department():
    assert '"legal",' in APP
    assert 'route: isLegalWorkspace ? "legal" : ""' in APP
    assert 'return renderLegalWorkspaceSurface(selectedRuns, scopedSelectedAgentCard)' in APP
    assert "Legal Pilot · controlled drafting and matter harness" in APP


def test_legal_workspace_uses_resizable_chat_and_functional_split():
    assert 'data-aion-legal-command-centre="true"' in APP
    assert 'data-aion-legal-pilot-thread="true"' in APP
    assert 'data-aion-legal-split-handle="true"' in APP
    assert 'data-aion-legal-workspace-pane="true"' in APP
    assert 'department_id: "legal"' in APP


def test_legal_workspace_has_matter_document_template_policy_and_signature_surfaces():
    for marker in (
        "Open legal matters",
        "Documents &amp; correspondence",
        "Templates",
        "Controlled signature envelopes",
        "Published and working documents",
        "Prepare signature request",
        "This creates a draft only",
        "Download evidence",
        "evidence-package/download",
        "Prepare replacement",
        "Verify history",
        "supersedes_envelope_id",
        "Separate-channel code",
        "Do not send this code in the same message as the link",
        "RETENTION · LEGAL HOLD · EXPORT",
        "Records controls",
        "content-free destruction receipt",
        "LINKED EVIDENCE",
        "RENEWALS · EXPIRIES · OBLIGATIONS",
        "HUMAN LEGAL PROFESSIONAL",
        "Tessaris never contacts or appoints a lawyer automatically",
        "professional-escalations",
        "Timeline &amp; proof cabinet",
        "SIGNING TIMELINE · PROOF CABINET",
        "HASH-CHAINED EVENT HISTORY",
        "independently trusted validator checkpoint",
        "Originals and extracted text are encrypted locally",
        "Secure upload",
        "LOCAL DOCUMENT REVIEW",
        "Automated suggestion",
        "not a legal determination",
        'signingRequest("/documents"',
        "/classification",
        "CLAUSE &amp; RISK TRIAGE",
        "Run local review",
        "Compare version",
        "Draft redline",
        "Record negotiation position",
        "not legal conclusions",
        "/contract-review",
        "/compare",
        "/redlines",
        "/negotiation-positions",
        "Approved template library",
        "No approved templates yet",
        "named qualified reviewer",
        'signingRequest("/templates/list")',
        "DRAFT_REQUIRES_QUALIFIED_REVIEW",
        "APPROVED_FOR_CONTROLLED_USE",
        "Record exact-version approval",
        "Create encrypted document draft",
        "/instantiate",
    ):
        assert marker in LEGAL


def test_legal_workspace_exposes_safety_boundary_and_loads_module():
    assert "Human review required" in APP
    assert "No legal representation" in APP
    assert "Consequential decisions and external sending remain with an authorised person" in APP
    assert '<script src="./aion_legal_workspace.js"></script>' in INDEX


def test_legal_chat_uploads_to_protected_storage_and_routes_through_local_harness():
    assert "selectAndUploadDocument" in LEGAL
    assert "result.document_id" in APP
    assert 'form.dataset.aionLegalAttachments = JSON.stringify([result.path])' not in APP
    assert 'if department == "legal"' in GATEWAY
    assert '"provider": "local_legal_harness"' in GATEWAY
