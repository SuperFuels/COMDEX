# backend/models/shipment.py

from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Shipment(Base):
    __tablename__ = "shipments"

    id          = Column(Integer, primary_key=True, index=True)
    product_id  = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity_kg = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at  = Column(DateTime, nullable=False, default=datetime.utcnow)

    # back‐ref to Product
    product = relationship("Product", back_populates="shipments")