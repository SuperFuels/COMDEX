import json

import pytest

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.xero_supplier_contact_service import XeroSupplierContactService
from backend.tests.test_finance_bookkeeping_service import configure


def test_supplier_contact_requires_exact_approval_and_readback(monkeypatch, tmp_path):
    repository, authority = configure(monkeypatch, tmp_path)
    service = XeroSupplierContactService(repository, authority)
    record = service.prepare("acme", name="FERRETERIA SOL", prepared_by_person_id="person.owner")
    assert record["payload"]["Contacts"][0]["ContactNumber"].startswith("TESS-")
    with pytest.raises(ValueError, match="payload_hash_mismatch"):
        service.approve("acme", record["contact_request_id"], approved_by_person_id="person.owner",
                        approved_payload_hash="wrong")
    record = service.approve("acme", record["contact_request_id"], approved_by_person_id="person.owner",
                             approved_payload_hash=record["payload_hash"])
    response = {"Contacts": [{**record["payload"]["Contacts"][0], "ContactID": "contact-1", "HasErrors": False}]}
    record = service.record_response("acme", record["contact_request_id"], response)
    verified = service.verify("acme", record["contact_request_id"], response)
    assert verified["status"] == "verified_in_xero"


def test_existing_contact_is_not_duplicated(monkeypatch, tmp_path):
    repository, authority = configure(monkeypatch, tmp_path)
    root = AIONBusinessPaths.business_container_dir("acme") / "integrations/xero"
    (root / "syncs/sync-1").mkdir(parents=True)
    (root / "connection.json").write_text(json.dumps({"latest_snapshot_ref": {"sync_id": "sync-1"}}))
    (root / "syncs/sync-1/contacts.json").write_text(json.dumps({"Contacts": [{"ContactID": "existing", "Name": "Supplier Ltd"}]}))
    service = XeroSupplierContactService(repository, authority)
    with pytest.raises(ValueError, match="already_exists:existing"):
        service.prepare("acme", name="supplier ltd", prepared_by_person_id="person.owner")
