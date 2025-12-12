# backend/modules/transactable_docs/transactable_doc_routes.py

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import hashlib
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Re-use dev escrow execution to make docs actually move PHO later
from backend.modules.escrow.escrow_routes import (
    DevEscrowCreate,
    create_dev_escrow,
)  # type: ignore[reportUnknownVariableType]  # noqa: E501

router = APIRouter(
    prefix="/transactable_docs",
    tags=["transactable-docs-dev"],
)


def _now_ms() -> int:
    return int(time.time() * 1000)


# ───────────────────────────────────────────────
# Dev model
# ───────────────────────────────────────────────

@dataclass
class DevDocSignature:
    signer: str
    signed_at_ms: int
    note: Optional[str] = None


@dataclass
class DevPaymentLeg:
    leg_id: str
    from_account: str
    to_account: str
    amount_pho: str
    channel: str          # e.g. "ESCROW_DEV", later "PHOTON_PAY"
    status: str           # "PENDING" | "EXECUTED" | "FAILED"
    created_at_ms: int
    executed_at_ms: Optional[int]
    ref_id: Optional[str]  # escrow_id / receipt_id / invoice_id etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DevTransactableDoc:
    doc_id: str
    title: str
    party_a: str
    party_b: str

    raw_text: str
    glyph_stream: Optional[str]

    status: str  # "DRAFT" | "ACTIVE" | "EXECUTED" | "CANCELLED"

    created_at_ms: int
    updated_at_ms: int
    executed_at_ms: Optional[int]

    # 🔐 Stable identity of the terms (what’s being signed)
    doc_hash: str

    # ✍️ Signature policy
    signatures: List[DevDocSignature]
    required_signers: List[str]          # e.g. [party_a, party_b]
    activation_policy: str               # "ALL" | "ANY"

    payment_legs: List[DevPaymentLeg]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["signatures"] = [asdict(s) for s in self.signatures]
        d["payment_legs"] = [pl.to_dict() for pl in self.payment_legs]
        return d

_DEV_DOCS: List[DevTransactableDoc] = []


def _compute_doc_hash(
    *,
    title: str,
    party_a: str,
    party_b: str,
    raw_text: str,
    glyph_stream: Optional[str],
    payment_legs: List[DevPaymentLeg],
) -> str:
    """
    Compute a stable hash over the *terms* of the document.

    We intentionally exclude status, signatures, timestamps, etc.
    so that doc_hash represents “what was signed”.
    """
    payload: Dict[str, Any] = {
        "title": title,
        "party_a": party_a,
        "party_b": party_b,
        "raw_text": raw_text,
        "glyph_stream": glyph_stream,
        "payment_legs": [
            {
                "from_account": pl.from_account,
                "to_account": pl.to_account,
                "amount_pho": pl.amount_pho,
                "channel": pl.channel,
            }
            for pl in payment_legs
        ],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# ───────────────────────────────────────────────
# Request models
# ───────────────────────────────────────────────


class DevPaymentLegInput(BaseModel):
    from_account: str
    to_account: str
    amount_pho: str
    channel: str = "ESCROW_DEV"  # for now we support only escrow-backed execution


class DevDocCreate(BaseModel):
    title: str
    party_a: str
    party_b: str
    raw_text: str
    glyph_stream: Optional[str] = None
    payment_legs: List[DevPaymentLegInput] = []

    # optional signature policy; defaults to [party_a, party_b] / "ALL"
    required_signers: Optional[List[str]] = None
    activation_policy: str = "ALL"


class DevDocId(BaseModel):
    doc_id: str


class DevDocUpdateText(BaseModel):
    doc_id: str
    raw_text: str
    glyph_stream: Optional[str] = None


class DevDocSign(BaseModel):
    doc_id: str
    signer: str
    note: Optional[str] = None


# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────


def _find_doc(doc_id: str) -> DevTransactableDoc:
    for d in _DEV_DOCS:
        if d.doc_id == doc_id:
            return d
    raise HTTPException(status_code=404, detail="doc not found")


# ───────────────────────────────────────────────
# Routes – list / create / get
# ───────────────────────────────────────────────


@router.get("/dev/list")
async def transactable_docs_dev_list() -> Dict[str, Any]:
    docs = sorted(_DEV_DOCS, key=lambda d: d.created_at_ms, reverse=True)
    return {"docs": [d.to_dict() for d in docs]}


@router.get("/dev/get")
async def transactable_docs_dev_get(doc_id: str) -> Dict[str, Any]:
    """
    Dev-only: fetch a single transactable document by ID.
    """
    doc = _find_doc(doc_id)
    return {"ok": True, "doc": doc.to_dict()}


@router.post("/dev/create")
async def transactable_docs_dev_create(body: DevDocCreate) -> Dict[str, Any]:
    now = _now_ms()
    doc_id = f"TDC_{uuid.uuid4().hex[:10]}"

    payment_legs: List[DevPaymentLeg] = []
    for pl_in in body.payment_legs:
        leg = DevPaymentLeg(
            leg_id=f"LEG_{uuid.uuid4().hex[:8]}",
            from_account=pl_in.from_account,
            to_account=pl_in.to_account,
            amount_pho=pl_in.amount_pho,
            channel=pl_in.channel,
            status="PENDING",
            created_at_ms=now,
            executed_at_ms=None,
            ref_id=None,
        )
        payment_legs.append(leg)

    title = body.title.strip() or doc_id
    party_a = body.party_a.strip()
    party_b = body.party_b.strip()

    required_signers = body.required_signers or [party_a, party_b]

    doc_hash = _compute_doc_hash(
        title=title,
        party_a=party_a,
        party_b=party_b,
        raw_text=body.raw_text,
        glyph_stream=body.glyph_stream,
        payment_legs=payment_legs,
    )

    doc = DevTransactableDoc(
        doc_id=doc_id,
        title=title,
        party_a=party_a,
        party_b=party_b,
        raw_text=body.raw_text,
        glyph_stream=body.glyph_stream,
        status="DRAFT",
        created_at_ms=now,
        updated_at_ms=now,
        executed_at_ms=None,
        doc_hash=doc_hash,
        signatures=[],
        required_signers=required_signers,
        activation_policy=body.activation_policy or "ALL",
        payment_legs=payment_legs,
    )
    _DEV_DOCS.append(doc)
    return {"ok": True, "doc": doc.to_dict()}


# ───────────────────────────────────────────────
# Routes – update, status, signatures
# ───────────────────────────────────────────────


@router.post("/dev/update_text")
async def transactable_docs_dev_update_text(body: DevDocUpdateText) -> Dict[str, Any]:
    doc = _find_doc(body.doc_id)
    if doc.status not in ("DRAFT", "ACTIVE"):
        raise HTTPException(
            status_code=400,
            detail="can only update text of DRAFT or ACTIVE docs",
        )

    doc.raw_text = body.raw_text
    doc.glyph_stream = body.glyph_stream
    doc.updated_at_ms = _now_ms()

    # changing terms invalidates prior signatures
    doc.signatures.clear()

    doc.doc_hash = _compute_doc_hash(
        title=doc.title,
        party_a=doc.party_a,
        party_b=doc.party_b,
        raw_text=doc.raw_text,
        glyph_stream=doc.glyph_stream,
        payment_legs=doc.payment_legs,
    )

    return {"ok": True, "doc": doc.to_dict()}


@router.post("/dev/activate")
async def transactable_docs_dev_activate(body: DevDocId) -> Dict[str, Any]:
    """
    Dev-only: move a document from DRAFT → ACTIVE.
    Enforces signature policy before activation.
    """
    doc = _find_doc(body.doc_id)
    if doc.status != "DRAFT":
        raise HTTPException(status_code=400, detail="only DRAFT docs can be activated")

    signed = {s.signer for s in doc.signatures}
    required = [s for s in doc.required_signers if s]

    policy = (doc.activation_policy or "ALL").upper()
    if policy == "ALL":
        missing = [s for s in required if s not in signed]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"missing signatures: {', '.join(missing)}",
            )
    elif policy == "ANY":
        if required and not (signed & set(required)):
            raise HTTPException(
                status_code=400,
                detail="at least one required signer must have signed",
            )

    doc.status = "ACTIVE"
    doc.updated_at_ms = _now_ms()
    return {"ok": True, "doc": doc.to_dict()}


@router.post("/dev/cancel")
async def transactable_docs_dev_cancel(body: DevDocId) -> Dict[str, Any]:
    """
    Dev-only: cancel a document (DRAFT or ACTIVE → CANCELLED).
    """
    doc = _find_doc(body.doc_id)
    if doc.status not in ("DRAFT", "ACTIVE"):
        raise HTTPException(status_code=400, detail="only DRAFT/ACTIVE can be cancelled")

    doc.status = "CANCELLED"
    doc.updated_at_ms = _now_ms()
    return {"ok": True, "doc": doc.to_dict()}


@router.post("/dev/sign")
async def transactable_docs_dev_sign(body: DevDocSign) -> Dict[str, Any]:
    """
    Dev-only: append a signature from a signer account.
    Allowed on DRAFT or ACTIVE docs.
    """
    doc = _find_doc(body.doc_id)
    if doc.status not in ("DRAFT", "ACTIVE"):
        raise HTTPException(status_code=400, detail="cannot sign non-active document")

    if any(s.signer == body.signer for s in doc.signatures):
        raise HTTPException(status_code=400, detail="signer has already signed")

    sig = DevDocSignature(
        signer=body.signer,
        signed_at_ms=_now_ms(),
        note=body.note,
    )
    doc.signatures.append(sig)
    doc.updated_at_ms = _now_ms()
    return {"ok": True, "doc": doc.to_dict()}

async def _execute_payment_leg(
    doc: DevTransactableDoc,
    leg: DevPaymentLeg,
    *,
    now_ms: int,
) -> Optional[Dict[str, Any]]:
    """
    Execute a single payment leg and return a small ref dict
    (or None if nothing to record).
    """
    if leg.status != "PENDING":
        return None

    if leg.channel == "ESCROW_DEV":
        esc_body = DevEscrowCreate(
            from_account=leg.from_account,
            to_account=leg.to_account,
            amount_pho=leg.amount_pho,
            kind="CONTRACT",
            label=doc.title,
            unlock_at_ms=None,
        )
        esc_result = await create_dev_escrow(esc_body)
        escrow = esc_result.get("escrow") or {}
        escrow_id = escrow.get("escrow_id")

        leg.status = "EXECUTED"
        leg.executed_at_ms = now_ms
        leg.ref_id = escrow_id or None

        return {
            "leg_id": leg.leg_id,
            "engine": "ESCROW_DEV",
            "ref_id": escrow_id,
        }

    elif leg.channel == "PHO_TRANSFER":
        # TODO: call real PHO wallet/ledger engine.
        # For now, stub a dev receipt.
        ref_id = f"DEV_PHO_TX_{uuid.uuid4().hex[:8]}"
        leg.status = "EXECUTED"
        leg.executed_at_ms = now_ms
        leg.ref_id = ref_id

        return {
            "leg_id": leg.leg_id,
            "engine": "PHO_TRANSFER",
            "ref_id": ref_id,
        }

    elif leg.channel == "PHOTON_PAY_INVOICE":
        # TODO: call photon_pay dev slice.
        ref_id = f"DEV_PHOTON_INV_{uuid.uuid4().hex[:8]}"
        leg.status = "EXECUTED"
        leg.executed_at_ms = now_ms
        leg.ref_id = ref_id

        return {
            "leg_id": leg.leg_id,
            "engine": "PHOTON_PAY_INVOICE",
            "ref_id": ref_id,
        }

    # Fallback: unknown channel
    leg.status = "FAILED"
    leg.executed_at_ms = now_ms
    leg.ref_id = None
    return {
        "leg_id": leg.leg_id,
        "engine": leg.channel,
        "ref_id": None,
        "error": "unknown_channel",
    }

# ───────────────────────────────────────────────
# Execution – wire into dev escrow
# ───────────────────────────────────────────────


@router.post("/dev/execute")
async def transactable_docs_dev_execute(body: DevDocId) -> Dict[str, Any]:
    """
    Dev-only: execute a transactable document.

    For now:
      • Only ACTIVE docs can be executed.
      • For each PENDING payment leg:
          – ESCROW_DEV        → dev escrow engine
          – PHO_TRANSFER      → stub PHO transfer receipt
          – PHOTON_PAY_INVOICE→ stub photon-pay invoice receipt
      • Marks legs as EXECUTED / FAILED and records ref_id.
      • Marks doc as EXECUTED once all legs processed.
    """
    doc = _find_doc(body.doc_id)
    if doc.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="only ACTIVE docs can be executed")

    now = _now_ms()
    refs: List[Dict[str, Any]] = []

    for leg in doc.payment_legs:
        ref = await _execute_payment_leg(doc, leg, now_ms=now)
        if ref is not None:
            refs.append(ref)

    doc.status = "EXECUTED"
    doc.executed_at_ms = now
    doc.updated_at_ms = now

    return {
        "ok": True,
        "doc": doc.to_dict(),
        "payment_refs": refs,
    }