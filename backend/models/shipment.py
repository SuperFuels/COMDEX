# backend/models/shipment.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Shipment(Base):
    __tablename__ = "shipments"

    id           = Column(Integer, primary_key=True, index=True)
    deal_id      = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity_kg  = Column(Float, nullable=False)
    shipped_at   = Column(DateTime, default=datetime.utcnow)
    status       = Column(String, default="pending")  # e.g. pending, in_transit, delivered

    deal         = relationship("Deal", back_populates="shipments")

    def __repr__(self):
        return (
            f"<Shipment(id={self.id!r}, deal_id={self.deal_id!r}, "
            f"quantity_kg={self.quantity_kg!r}, status={self.status!r})>"
        )