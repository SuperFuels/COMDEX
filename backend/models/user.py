from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import relationship
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id               = Column(Integer,   primary_key=True, index=True)
    name             = Column(String,    nullable=False)
    email            = Column(String,    unique=True, index=True, nullable=False)
    password_hash    = Column(String,    nullable=False)
    wallet_address   = Column(String,    unique=True, index=True, nullable=True)
    role             = Column(String,    nullable=False, default="buyer")  # buyer or supplier
    business_name    = Column(String,    nullable=True)  # supplier only
    address          = Column(String,    nullable=True)  # supplier only
    delivery_address = Column(String,    nullable=True)  # supplier only
    products         = Column(JSON,      nullable=True)  # list of product slugs for supplier
    monthly_spend    = Column(String,    nullable=True)  # buyer only
    created_at       = Column(DateTime,  nullable=False, default=datetime.utcnow)
    updated_at       = Column(DateTime,  nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ─── Relationships ────────────────────────────────────────────────────────────

    # Products owned by this supplier
    products_owned = relationship(
        "Product",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    # Deals where this user is the buyer
    buyer_deals = relationship(
        "Deal",
        back_populates="buyer",
        foreign_keys="[Deal.buyer_id]",
        cascade="all, delete-orphan",
    )

    # Deals where this user is the supplier
    supplier_deals = relationship(
        "Deal",
        back_populates="supplier",
        foreign_keys="[Deal.supplier_id]",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<User(id={self.id!r}, email={self.email!r}, "
            f"wallet_address={self.wallet_address!r}, role={self.role!r})>"
        )
