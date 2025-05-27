# backend/models/product.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database import Base

class Product(Base):
    __tablename__ = "products"

    id            = Column(Integer,   primary_key=True, index=True)
    name          = Column(String,    nullable=False)
    description   = Column(String,    nullable=True)
    price         = Column(Float,     nullable=False)
    owner_id      = Column(Integer,   ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at    = Column(DateTime,  nullable=False, default=datetime.utcnow)

    # ─── the two new columns from your migration
    change_pct    = Column(Float,     nullable=False, default=0.0)
    rating        = Column(Float,     nullable=False, default=0.0)

    # ─── relationships
    owner = relationship("User",   back_populates="products")
    deals = relationship(
        "Deal",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<Product("
            f"id={self.id!r}, name={self.name!r}, price={self.price!r}, "
            f"owner_id={self.owner_id!r}, change_pct={self.change_pct!r}, "
            f"rating={self.rating!r}"
            f")>"
        )