# File: backend/routes/deal.py

import os
import json
import logging
from io import BytesIO
from typing import List, Tuple

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Body,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from web3 import Web3

from backend.database import Base, engine, get_db
from backend.models.user import User
from backend.models.product import Product
from backend.schemas.deal import DealCreate, DealOut, DealStatusUpdate
from backend.utils.auth import get_current_user

router = APIRouter(
    prefix="/deals",    # ← all routes now under /api/deals
    tags=["Deals"],
)

logger = logging.getLogger(__name__)

# ─── ABI Setup ────────────────────────────────────────────────────
ABI_PATH = os.path.join(os.path.dirname(__file__), "../abi/GLUEscrow.json")
with open(ABI_PATH, "r") as f:
    artifact = json.load(f)
ESCROW_ABI = artifact.get("abi", [])
if not ESCROW_ABI:
    raise RuntimeError("ABI not found in GLUEscrow.json")


def get_web3_contract() -> Tuple[Web3, any, any]:
    RPC_URL = os.getenv("WEB3_PROVIDER_URL")
    if not RPC_URL:
        raise RuntimeError("Missing WEB3_PROVIDER_URL")

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise RuntimeError(f"Cannot connect to Web3 provider at {RPC_URL}")

    addr = os.getenv("ESCROW_CONTRACT_ADDRESS")
    if not addr:
        raise RuntimeError("Missing ESCROW_CONTRACT_ADDRESS")
    escrow_addr = Web3.to_checksum_address(addr)

    contract = w3.eth.contract(address=escrow_addr, abi=ESCROW_ABI)

    pk = os.getenv("DEPLOYER_PRIVATE_KEY")
    if not pk:
        raise RuntimeError("Missing DEPLOYER_PRIVATE_KEY")
    deployer = w3.eth.account.from_key(pk)

    return w3, contract, deployer


@router.post(
    "/",
    response_model=DealOut,
    status_code=status.HTTP_201_CREATED,
)
def create_deal(
    deal_data: DealCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == deal_data.product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    supplier = db.query(User).filter(User.email == product.owner_email).first()
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")

    total_price = deal_data.quantity_kg * product.price_per_kg
    payload = {
        **deal_data.dict(),
        "buyer_email": current_user.email,
        "buyer_id": current_user.id,
        "supplier_email": supplier.email,
        "supplier_id": supplier.id,
        "product_title": product.title,
        "total_price": total_price,
        "status": "negotiation",
    }

    try:
        deal = Deal(**payload)
        db.add(deal)
        db.commit()
        db.refresh(deal)
        deal.supplier_wallet_address = supplier.wallet_address or ""
        return deal
    except Exception as e:
        logger.error("Failed to create deal", exc_info=e)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create deal"
        )


@router.get(
    "/",
    response_model=List[DealOut],
)
def list_deals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deals = (
        db.query(Deal)
          .filter(
              (Deal.buyer_email == current_user.email) |
              (Deal.supplier_email == current_user.email)
          )
          .all()
    )
    for d in deals:
        sup = db.query(User).filter(User.email == d.supplier_email).first()
        d.supplier_wallet_address = sup.wallet_address or ""
    return deals


@router.get(
    "/{deal_id}",
    response_model=DealOut,
)
def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    if current_user.email not in (deal.buyer_email, deal.supplier_email):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    sup = db.query(User).filter(User.email == deal.supplier_email).first()
    deal.supplier_wallet_address = sup.wallet_address or ""
    return deal


@router.put(
    "/{deal_id}/status",
    response_model=DealOut,
)
def update_status(
    deal_id: int,
    data: DealStatusUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    if current_user.email not in (deal.buyer_email, deal.supplier_email):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    if data.status not in {"negotiation", "confirmed", "completed"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")

    deal.status = data.status
    db.commit()
    db.refresh(deal)

    sup = db.query(User).filter(User.email == deal.supplier_email).first()
    deal.supplier_wallet_address = sup.wallet_address or ""
    return deal


@router.get("/{deal_id}/pdf")
def get_deal_pdf(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    if current_user.email not in (deal.buyer_email, deal.supplier_email):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    try:
        from weasyprint import HTML
    except ImportError as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WeasyPrint missing: " + str(e)
        )

    html = f"""
    <h1>Deal #{deal.id}</h1>
    <p><strong>Buyer:</strong> {deal.buyer_email}</p>
    <p><strong>Supplier:</strong> {deal.supplier_email}</p>
    <p><strong>Product:</strong> {deal.product_title}</p>
    <p><strong>Quantity:</strong> {deal.quantity_kg} kg</p>
    <p><strong>Total Price:</strong> ${deal.total_price}</p>
    <p><strong>Status:</strong> {deal.status}</p>
    """
    buf = BytesIO()
    HTML(string=html).write_pdf(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="deal_{deal_id}.pdf"'}
    )


@router.post("/{deal_id}/release")
def release_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    if current_user.email != deal.supplier_email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    w3, contract, deployer = get_web3_contract()
    nonce = w3.eth.get_transaction_count(deployer.address)
    tx = contract.functions.release(deal_id).build_transaction({
        "from": deployer.address,
        "nonce": nonce,
        "gas": 200_000,
    })
    signed = deployer.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    deal.status = "released"
    db.commit()
    db.refresh(deal)

    logger.info(f"Deal {deal_id} released on-chain: {receipt.transactionHash.hex()}")
    return {"status": "released", "txHash": receipt.transactionHash.hex()}