from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = { "extend_existing": True }

    id           = Column(Integer, primary_key=True, index=True)
    deal_id      = Column(Integer, ForeignKey("deals.id",    ondelete="CASCADE"), nullable=False, index=True)
    product_id   = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True,  index=True)

    quantity_kg  = Column(Float,   nullable=False)
    shipped_at   = Column(DateTime, nullable=False, default=datetime.utcnow)
    status       = Column(String,  nullable=False, server_default="pending")

    # ─── Relationships ─────────────────────────────────────────────────────────
    deal         = relationship("Deal",    back_populates="shipments")
    product      = relationship("Product", back_populates="shipments")

    def __repr__(self):
        return (
            f"<Shipment("
            f"id={self.id!r}, deal_id={self.deal_id!r}, product_id={self.product_id!r}, "
            f"quantity_kg={self.quantity_kg!r}, status={self.status!r}"
            f")>"
        )