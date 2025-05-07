# backend/routes/deal.py

import os
import json
import logging
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from weasyprint import HTML
from web3 import Web3

from database import get_db
from models.deal import Deal
from models.product import Product
from models.user import User
from schemas.deal import DealCreate, DealOut, DealStatusUpdate
from utils.auth import get_current_user

router = APIRouter(prefix="/deals", tags=["Deals"])
logger = logging.getLogger(__name__)

# ─── On-chain setup ───────────────────────────

# 1) Load escrow ABI
ABI_PATH = os.path.join(os.path.dirname(__file__), "../abi/GLUEscrow.json")
with open(ABI_PATH, "r") as f:
    artifact = json.load(f)
    ESCROW_ABI = artifact["abi"]

# 2) Connect to your local Hardhat node
WEB3_PROVIDER_URL = os.getenv("WEB3_PROVIDER_URL", "http://127.0.0.1:8545")
W3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
if not W3.is_connected():
    raise RuntimeError(f"Cannot connect to Web3 provider at {WEB3_PROVIDER_URL}")

# 3) Read & checksum the escrow contract address
escrow_addr_env = os.getenv("ESCROW_CONTRACT_ADDRESS")
if not escrow_addr_env:
    raise RuntimeError("ESCROW_CONTRACT_ADDRESS environment variable is not set")
ESCROW_ADDR = Web3.to_checksum_address(escrow_addr_env)

# 4) Instantiate the on-chain contract
ESCROW_CONTRACT = W3.eth.contract(address=ESCROW_ADDR, abi=ESCROW_ABI)

# 5) Load deployer key & account
deployer_pk = os.getenv("DEPLOYER_PRIVATE_KEY")
if not deployer_pk:
    raise RuntimeError("DEPLOYER_PRIVATE_KEY environment variable is not set")
DEPLOYER_ACCT = W3.eth.account.from_key(deployer_pk)

# ─── REST endpoints ───────────────────────────
    
@router.post("/", response_model=DealOut, status_code=status.HTTP_201_CREATED)
def create_deal(
    deal_data: DealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1) fetch product
    product = db.query(Product).filter(Product.id == deal_data.product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    # 2) fetch supplier user
    supplier = db.query(User).filter(User.email == product.owner_email).first()
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier user not found")

    # 3) build full payload
    payload = deal_data.dict()
    payload.update({
        "buyer_email":    current_user.email,
        "buyer_id":       current_user.id,
        "supplier_email": supplier.email,
        "supplier_id":    supplier.id,
        "product_title":  product.title,
        "total_price":    deal_data.quantity_kg * product.price_per_kg,
        "status":         "negotiation",
    })

    # 4) persist
    try:
        new_deal = Deal(**payload)
        db.add(new_deal)
        db.commit()
        db.refresh(new_deal)
        logger.info(f"✅ Deal created: {new_deal.id}")
        # attach supplier_wallet_address before returning
        new_deal.supplier_wallet_address = supplier.wallet_address or ""
        return new_deal
    except Exception as e:
        logger.error(f"❌ Failed to create deal: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Failed to create deal"
        )

@router.get("/", response_model=List[DealOut])
def get_user_deals(
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
    # attach on-chain supplier address
    for d in deals:
        sup = db.query(User).filter(User.email == d.supplier_email).first()
        d.supplier_wallet_address = sup.wallet_address or ""
    return deals

@router.get("/{deal_id}", response_model=DealOut)
def get_deal_by_id(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).get(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    if current_user.email not in {deal.buyer_email, deal.supplier_email}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to view this deal")
    # attach on-chain supplier address
    sup = db.query(User).filter(User.email == deal.supplier_email).first()
    deal.supplier_wallet_address = sup.wallet_address or ""
    return deal

@router.put("/{deal_id}/status", response_model=DealOut, summary="Update deal status")
def update_deal_status(
    deal_id: int,
    data: DealStatusUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).get(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    if current_user.email not in {deal.buyer_email, deal.supplier_email}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to update this deal")
    if data.status not in ["negotiation", "confirmed", "completed"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")

    deal.status = data.status
    db.commit()
    db.refresh(deal)
    # attach on-chain supplier address
    sup = db.query(User).filter(User.email == deal.supplier_email).first()
    deal.supplier_wallet_address = sup.wallet_address or ""
    return deal

@router.get("/{deal_id}/pdf", summary="Download deal summary as PDF")
def generate_deal_pdf(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).get(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    if current_user.email not in {deal.buyer_email, deal.supplier_email}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to view this deal")

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

@router.post("/{deal_id}/release", summary="Release funds on-chain")
def release_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1) load deal & auth
    deal = db.query(Deal).get(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    if current_user.email != deal.supplier_email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    # 2) build, sign & send on-chain tx
    nonce = W3.eth.get_transaction_count(DEPLOYER_ACCT.address)
    tx = ESCROW_CONTRACT.functions.release(deal_id).build_transaction({
        "from":  DEPLOYER_ACCT.address,
        "nonce": nonce,
        "gas":   200_000,
    })
    signed = DEPLOYER_ACCT.sign_transaction(tx)
    # NOTE: use `.raw_transaction`, not `.rawTransaction`
    tx_hash = W3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = W3.eth.wait_for_transaction_receipt(tx_hash)

    # 3) update DB
    deal.status = "released"
    db.commit()
    db.refresh(deal)

    logger.info(f"🔓 Deal {deal_id} released on-chain, tx={receipt.transactionHash.hex()}")
    return {"status": "released", "txHash": receipt.transactionHash.hex()}

