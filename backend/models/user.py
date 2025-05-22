# backend/models/user.py

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class User(Base):
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String, nullable=False)
    email          = Column(String, unique=True, index=True, nullable=False)
    password_hash  = Column(String, nullable=False)
    wallet_address = Column(String, unique=True, index=True, nullable=True)
    role           = Column(String, default="user", nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────────────────
    # A user can own many products
    products = relationship(
        "Product",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    # Deals where this user is the buyer
    buyer_deals = relationship(
        "Deal",
        back_populates="buyer",
        foreign_keys="Deal.buyer_id",
        cascade="all, delete-orphan",
    )

    # Deals where this user is the supplier
    supplier_deals = relationship(
        "Deal",
        back_populates="supplier",
        foreign_keys="Deal.supplier_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<User("
            f"id={self.id!r}, email={self.email!r}, wallet={self.wallet_address!r}, "
            f"role={self.role!r}"
            f")>"
        )
