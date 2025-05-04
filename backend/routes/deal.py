# backend/routes/deal.py

import logging
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from weasyprint import HTML

from database import get_db
from models.deal import Deal
from models.product import Product
from models.user import User
from schemas.deal import DealCreate, DealOut
from utils.auth import get_current_user

router = APIRouter(tags=["Deals"])
logger = logging.getLogger(__name__)


@router.post(
    "/", response_model=DealOut, status_code=status.HTTP_201_CREATED
)
def create_deal(
    deal_data: DealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new deal.  Looks up the product to fill in supplier_email,
    product_title, total_price, buyer_id and supplier_id.
    """
    # 1) fetch product
    product = db.query(Product).filter(Product.id == deal_data.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # 2) fetch supplier user (to get supplier_id)
    supplier = db.query(User).filter(User.email == product.owner_email).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier user not found"
        )

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
        logger.info(f"✅ Deal created: {new_deal.id} by {current_user.email}")
        return new_deal

    except Exception as e:
        logger.error(f"❌ Failed to create deal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create deal"
        )
    
    
@router.get("/", response_model=List[DealOut])
def get_user_deals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all deals where the logged‑in user is buyer or supplier.
    """
    try:
        deals = (
            db.query(Deal)
              .filter(
                  (Deal.buyer_email == current_user.email) |
                  (Deal.supplier_email == current_user.email)
              )
              .all()
        )
        logger.info(f"✅ {len(deals)} deal(s) fetched for {current_user.email}")
        return deals

    except Exception as e:  
        logger.error(f"❌ Failed to fetch deals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch deals"
        )


@router.get("/{deal_id}", response_model=DealOut)
def get_deal_by_id(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch a single deal by ID (only if you’re the buyer or supplier).
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        logger.warning(f"⚠️ Deal {deal_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found"
        )
            
    if current_user.email not in {deal.buyer_email, deal.supplier_email}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this deal"
        )
        
    logger.info(f"✅ Deal {deal_id} fetched by {current_user.email}")
    return deal
        
        
@router.get("/{deal_id}/pdf", summary="Download deal summary as PDF")
def generate_deal_pdf(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate and stream a PDF summary of the deal.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        logger.warning(f"⚠️ Deal {deal_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found"
        )
       
    if current_user.email not in {deal.buyer_email, deal.supplier_email}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this deal"
        )
        
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
    return StreamingResponse(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="deal_{deal_id}.pdf"'},
    )

