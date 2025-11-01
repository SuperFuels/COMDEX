from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models.product import Product
from backend.models.user import User
from backend.utils.auth import get_current_user

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter(
    prefix="/supplier",
    tags=["Supplier"],
)

@router.get(
    "/dashboard",
    summary="Supplier dashboard: metrics + products",
)
@router.get(
    "/dashboard/",
    include_in_schema=False,
)
def supplier_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session        = Depends(get_db),
):
    """
    Returns:
      - totalSalesToday: int
      - activeListings: int
      - openOrders: int
      - proceeds30d: float
      - feedbackRating: float
      - products: list of { id, title, description, price_per_kg, origin_country, image_url }
    """
    if current_user.role != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only suppliers can access this endpoint"
        )

    # TODO: hook up real aggregates here
    total_sales     = 0
    open_orders     = 0
    proceeds_30d    = 0.0
    feedback_rating = 0.0

    q = db.query(Product).filter(Product.owner_email == current_user.email)
    active_listings = q.count()

    products = [
        {
            "id":             p.id,
            "title":          p.title,
            "description":    p.description,
            "price_per_kg":   p.price_per_kg,
            "origin_country": p.origin_country,
            "image_url":      p.image_url or "",
        }
        for p in q.all()
    ]

    return {
        "totalSalesToday": total_sales,
        "activeListings":  active_listings,
        "openOrders":      open_orders,
        "proceeds30d":     proceeds_30d,
        "feedbackRating":  feedback_rating,
        "products":        products,
    }

@router.get(
    "/products",
    summary="List this supplier's products",
)
def list_my_products(
    current_user: User = Depends(get_current_user),
    db: Session        = Depends(get_db),
):
    """
    GET /api/supplier/products
    Just returns the `products` array for the current supplier (no metrics).
    """
    if current_user.role != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only suppliers can access this endpoint"
        )

    prods = (
        db.query(Product)
          .filter(Product.owner_email == current_user.email)
          .all()
    )
    return [
        {
            "id":             p.id,
            "title":          p.title,
            "description":    p.description,
            "price_per_kg":   p.price_per_kg,
            "origin_country": p.origin_country,
            "image_url":      p.image_url or "",
        }
        for p in prods
    ]