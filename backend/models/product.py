from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database import Base

class Product(Base):
    __tablename__ = "products"

    id                = Column(Integer, primary_key=True, index=True)
    owner_email       = Column(String, ForeignKey("users.email", ondelete="CASCADE"), nullable=False, index=True)
    title             = Column(String, nullable=False)
    description       = Column(Text, nullable=True)
    price_per_kg      = Column(Float, nullable=False)
    origin_country    = Column(String, nullable=True)
    category          = Column(String, nullable=True)
    image_url         = Column(String, nullable=True)
    change_pct        = Column(Float, nullable=False, default=0.0)
    rating            = Column(Float, nullable=False, default=0.0)
    batch_number      = Column(String, nullable=True)
    trace_id          = Column(String, nullable=True)
    certificate_url   = Column(String, nullable=True)
    blockchain_tx_hash= Column(String, nullable=True)
    created_at        = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    owner = relationship(
        "User",
        back_populates="products_owned"
    )
    deals = relationship(
        "Deal",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<Product(id={self.id!r}, title={self.title!r}, "
            f"owner_email={self.owner_email!r})>"
        )
