# backend/models/product.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database import Base

class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}

    # ─── Columns ───────────────────────────────────────────────────────────────
    id             = Column(Integer, primary_key=True, index=True)
    title          = Column(String,  nullable=False, unique=True, index=True)
    description    = Column(String,  nullable=True)
    price_per_kg   = Column(Float,   nullable=False, default=0.0)
    image_url      = Column(String,  nullable=True)
    origin_country = Column(String,  nullable=True)
    category       = Column(String,  nullable=True)
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)

    # ─── Foreign key & relationship to User ────────────────────────────────────
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner    = relationship(
        "User",
        back_populates="products_owned",     # <-- matches User.products_owned
    )

    # ─── Relationships to Deal & Shipment ───────────────────────────────────────
    deals     = relationship(
        "Deal",
        back_populates="product",            # <-- matches Deal.product
        cascade="all, delete-orphan",
    )
    shipments = relationship(
        "Shipment",
        back_populates="product",            # <-- matches Shipment.product
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<Product(id={self.id!r}, title={self.title!r}, "
            f"price_per_kg={self.price_per_kg!r})>"
        )