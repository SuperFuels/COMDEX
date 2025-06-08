# File: backend/routes/supplier.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.product import Product
from ..models.user import User
from ..utils.auth import get_current_user

router = APIRouter(
    prefix="/api/supplier",
    tags=["Supplier"],
)


@router.get("/dashboard")
def supplier_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session        = Depends(get_db),
):
    """
    Supplier dashboard metrics:
      - totalSalesToday
      - activeListings
      - openOrders
      - proceeds30d
      - feedbackRating
      - products (list of this supplier's products)
    """
    # 1) Only suppliers allowed
    if current_user.role != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only suppliers can access this endpoint"
        )

    # 2) TODO: Replace these stubs with real, per-supplier calculations
    total_sales     = 0
    open_orders     = 0
    proceeds_30d    = 0.0
    feedback_rating = 0.0

    # 3) Active listings = number of products this supplier owns
    products_q = (
        db.query(Product)
          .filter(Product.owner_email == current_user.email)
    )
    active_listings = products_q.count()

    # 4) Build the products array
    products = []
    for p in products_q.all():
        products.append({
            "id":             p.id,
            "title":          p.title,
            "description":    p.description,
            "price_per_kg":   p.price_per_kg,
            "origin_country": p.origin_country,
            "image_url":      p.image_url or "",
        })

    return {
        "totalSalesToday": total_sales,
        "activeListings":  active_listings,
        "openOrders":      open_orders,
        "proceeds30d":     proceeds_30d,
        "feedbackRating":  feedback_rating,
        "products":        products,
    }