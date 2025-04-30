from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.deal import Deal
from schemas.deal import DealCreate, DealOut
from typing import List
from utils.auth import get_current_user
from fastapi.responses import StreamingResponse
from weasyprint import HTML
from io import BytesIO
import logging

# ✅ Initialize router
router = APIRouter(
    tags=["Deals"]
)

# ✅ Logger
logger = logging.getLogger(__name__)

# ✅ POST: Create a new deal
@router.post("/", response_model=DealOut)
def create_deal(
    deal_data: DealCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        new_deal = Deal(**deal_data.dict())
        db.add(new_deal)
        db.commit()
        db.refresh(new_deal)
        logger.info(f"✅ Deal created: {new_deal.id} by {current_user.email}")
        return new_deal
    except Exception as e:
        logger.error(f"❌ Failed to create deal: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create deal")

# ✅ GET: All deals for authenticated user (as buyer or supplier)
@router.get("/", response_model=List[DealOut])
def get_user_deals(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        deals = db.query(Deal).filter(
            (Deal.buyer_email == current_user.email) |
            (Deal.supplier_email == current_user.email)
        ).all()
        logger.info(f"✅ {len(deals)} deal(s) fetched for {current_user.email}")
        return deals
    except Exception as e:
        logger.error(f"❌ Failed to fetch deals: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch deals")

# ✅ GET: Deal by ID
@router.get("/{deal_id}", response_model=DealOut)
def get_deal_by_id(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if not deal:
        logger.warning(f"⚠️ Deal {deal_id} not found")
        raise HTTPException(status_code=404, detail="Deal not found")

    if current_user.email not in [deal.buyer_email, deal.supplier_email]:
        raise HTTPException(status_code=403, detail="Not authorized to view this deal")

    logger.info(f"✅ Deal {deal_id} fetched by {current_user.email}")
    return deal

# ✅ GET: Generate PDF for deal
@router.get("/{deal_id}/pdf")
def generate_deal_pdf(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if not deal:
        logger.warning(f"⚠️ Deal {deal_id} not found")
        raise HTTPException(status_code=404, detail="Deal not found")

    if current_user.email not in [deal.buyer_email, deal.supplier_email]:
        raise HTTPException(status_code=403, detail="Not authorized to view this PDF")

    html_content = f"""
    <h1>Deal Summary</h1>
    <p><strong>Buyer:</strong> {deal.buyer_email}</p>
    <p><strong>Supplier:</strong> {deal.supplier_email}</p>
    <p><strong>Product:</strong> {deal.product_title}</p>
    <p><strong>Quantity (kg):</strong> {deal.quantity_kg}</p>
    <p><strong>Total Price:</strong> ${deal.total_price}</p>
    <p><strong>Status:</strong> {deal.status}</p>
    <p><strong>Created:</strong> {deal.created_at.strftime('%Y-%m-%d')}</p>
    """

    pdf_bytes = BytesIO()
    HTML(string=html_content).write_pdf(pdf_bytes)
    pdf_bytes.seek(0)

    logger.info(f"✅ PDF generated for deal {deal_id}")
    return StreamingResponse(pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=deal_{deal_id}.pdf"
    })

