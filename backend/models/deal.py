# backend/models/deal.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database import Base

class Deal(Base):
    __tablename__ = "deals"

    id          = Column(Integer, primary_key=True, index=True)
    product_id  = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    buyer_id    = Column(Integer, ForeignKey("users.id",    ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("users.id",    ondelete="CASCADE"), nullable=False, index=True)

    price       = Column(Float,   nullable=False)
    status      = Column(String,  nullable=False, server_default="pending")
    created_at  = Column(DateTime, nullable=False, default=datetime.utcnow)

    # ORM relationships
    product      = relationship("Product", back_populates="deals")
    buyer        = relationship("User",    back_populates="buyer_deals",    foreign_keys=[buyer_id])
    supplier     = relationship("User",    back_populates="supplier_deals", foreign_keys=[supplier_id])

    # one‐to‐one to Contract (if you keep that)
    contract     = relationship("Contract", back_populates="deal", uselist=False)

    def __repr__(self):
        return (
            f"<Deal("
            f"id={self.id!r}, product_id={self.product_id!r}, "
            f"buyer_id={self.buyer_id!r}, supplier_id={self.supplier_id!r}, "
            f"price={self.price!r}, status={self.status!r}"
            f")>"
        )