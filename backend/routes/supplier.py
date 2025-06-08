# File: backend/routes/supplier.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.product import Product

router = APIRouter(prefix="/api/supplier", tags=["Supplier"])

@router.get("/dashboard")
def supplier_dashboard(
    db: Session = Depends(get_db),
    # Optionally, inject current_user here if you only want that supplier’s data:
    # current_user: User = Depends(get_current_user)
):
    """
    TODO: swap out these stubs for real queries filtered by the logged-in supplier.
    """
    total_sales     = 0
    active_listings = db.query(Product).count()
    open_orders     = 0
    proceeds_30d    = 0.0
    feedback_rating = 0.0

    return {
        "totalSalesToday":  total_sales,
        "activeListings":   active_listings,
        "openOrders":       open_orders,
        "proceeds30d":      proceeds_30d,
        "feedbackRating":   feedback_rating,
        "products":         [],  # or fetch a list of this supplier’s products
    }