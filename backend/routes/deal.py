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

router = APIRouter(
    prefix="/deals",
    tags=["Deals"]
)

# ✅ Create new deal
@router.post("/create", response_model=DealOut)
def create_deal(
    deal_data: DealCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Endpoint to create a new deal.
    The data is received as a DealCreate model and saved in the database.
    """
    # Create a new deal instance using the received data
    new_deal = Deal(**deal_data.dict())

    # Add the new deal to the database session and commit it
    db.add(new_deal)
    db.commit()
    db.refresh(new_deal)  # Refresh the instance to reflect the committed data

    # Return the newly created deal
    return new_deal

# ✅ GET: Fetch all deals for the authenticated user
@router.get("/", response_model=List[DealOut])
def get_user_deals(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Endpoint to fetch all deals for the authenticated user.
    """
    # Query the database for all deals associated with the current user
    deals = db.query(Deal).filter(Deal.buyer_email == current_user).all()

    # Return the list of deals
    return deals

# ✅ Download PDF summary
@router.get("/{deal_id}/pdf")
def generate_deal_pdf(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Endpoint to generate and download a PDF summarizing the deal.
    The PDF includes buyer, supplier, product, quantity, and total price.
    """
    # Fetch the deal from the database
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    # If the deal does not exist, raise an HTTPException
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Construct HTML content for the PDF
    html_content = f"""
    <h1>Deal Summary</h1> <p><strong>Buyer:</strong> {deal.buyer_email}</p>
    <p><strong>Supplier:</strong> {deal.supplier_email}</p>
    <p><strong>Product:</strong> {deal.product_title}</p>
    <p><strong>Quantity (kg):</strong> {deal.quantity_kg}</p>
    <p><strong>Total Price:</strong> ${deal.total_price}</p>     
    """
    
    # Create a BytesIO object to hold the generated PDF
    pdf_bytes = BytesIO()
    
    # Generate the PDF from the HTML content using WeasyPrint
    HTML(string=html_content).write_pdf(pdf_bytes)
    pdf_bytes.seek(0)  # Reset the pointer to the start of the BytesIO buffer   

    # Return the PDF as a StreamingResponse to allow download
    return StreamingResponse(pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=deal_{deal_id}.pdf"
    })

